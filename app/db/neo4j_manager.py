# app/db/neo4j_manager.py
import logging
from neo4j import AsyncGraphDatabase, AsyncSession, AsyncTransaction, RoutingControl
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

class Neo4jManager:
    def __init__(self, uri: str, user: str, password: str):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None

    async def connect(self):
        """Establishes the connection to the Neo4j database."""
        if not self._driver:
            logger.info(f"Connecting to Neo4j at {self._uri}")
            try:
                self._driver = AsyncGraphDatabase.driver(self._uri, auth=(self._user, self._password))
                await self._driver.verify_connectivity()
                logger.info("Neo4j connection established.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}", exc_info=True)
                raise

    async def close(self):
        """Closes the connection to the Neo4j database."""
        if self._driver:
            logger.info("Closing Neo4j connection.")
            await self._driver.close()
            self._driver = None

    @asynccontextmanager
    async def get_session(self, database: str = "neo4j") -> AsyncSession:
        """Provides an async context manager for a Neo4j session."""
        if not self._driver:
            await self.connect()
        session: AsyncSession = None
        try:
            session = self._driver.session(database=database)
            yield session
        finally:
            if session:
                await session.close()

    async def run_query(self, query: str, parameters: Optional[Dict[str, Any]] = None, database: str = "neo4j"):
        """Runs a Cypher query within a transaction."""
        async with self.get_session(database=database) as session:
            try:
                result = await session.execute_write(self._execute_query, query, parameters)
                return result
            except Exception as e:
                logger.error(f"Error running query: {query} | Params: {parameters} | Error: {e}", exc_info=True)
                raise

    @staticmethod
    async def _execute_query(tx: AsyncTransaction, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Helper function to execute a query within a transaction context."""
        result = await tx.run(query, parameters)
        # Consuming the result is often needed to ensure the transaction completes
        # Return records if needed, or just summary/None
        records = await result.data()
        summary = await result.consume()
        # logger.debug(f"Query finished. Summary: {summary}")
        # Return records for potential use, e.g., fetching data
        return records

    async def ensure_constraints_indexes(self, dimensions: int):
        """Creates necessary constraints and indexes if they don't exist."""
        logger.info("Ensuring Neo4j constraints and vector index...")
        constraint_queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.url IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE", # Unique within the repo context ideally, simple approach first
            "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE fn.unique_id IS UNIQUE", # Requires generating a unique ID
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Class) REQUIRE cl.unique_id IS UNIQUE", # Requires generating a unique ID
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cc:CodeChunk) REQUIRE cc.chunk_id IS UNIQUE", # Requires generating a unique ID
        ]
        # Vector Index (adjust name and dimensions as needed)
        vector_index_query = f"""
        CREATE VECTOR INDEX `code_chunk_embeddings` IF NOT EXISTS
        FOR (c:CodeChunk) ON (c.embedding)
        OPTIONS {{ indexConfig: {{
            `vector.dimensions`: {dimensions},
            `vector.similarity_function`: 'cosine'
        }} }}
        """

        async with self.get_session() as session:
            for query in constraint_queries:
                try:
                    logger.debug(f"Running: {query}")
                    await session.run(query)
                except Exception as e:
                    logger.warning(f"Could not create constraint (may already exist): {e}")
            try:
                logger.debug(f"Running: {vector_index_query}")
                await session.run(vector_index_query)
            except Exception as e:
                logger.warning(f"Could not create vector index: {e}")
        logger.info("Constraints and vector index check complete.")

    async def get_repository_status(self, repo_url: str) -> Optional[str]:
        """Gets the last indexed commit SHA for a repository."""
        query = "MATCH (r:Repository {url: $repo_url}) RETURN r.last_indexed_commit_sha AS sha"
        parameters = {"repo_url": repo_url}
        async with self.get_session() as session:
            result = await session.run(query, parameters)
            record = await result.single()
            return record["sha"] if record else None

    async def clear_repository_data(self, repo_url: str):
        """Deletes all nodes and relationships associated with a specific repository."""
        logger.warning(f"Clearing all data for repository: {repo_url}")
        # This query finds all nodes connected to the repository (including chunks) and detaches/deletes them
        # Be CAREFUL with this in production. Consider soft deletes or versioning instead.
        query = """
        MATCH (repo:Repository {url: $repo_url})
        OPTIONAL MATCH (repo)<-[:BELONGS_TO*0..]-(related_node)
        DETACH DELETE repo, related_node
        """
        parameters = {"repo_url": repo_url}
        async with self.get_session() as session:
             await session.execute_write(self._execute_query, query, parameters)
        logger.info(f"Successfully cleared data for repository: {repo_url}")



    async def batch_merge_nodes_relationships(self, batch: List[Dict[str, Any]]):
        """
        Merges nodes and relationships in batches using UNWIND.
        # ... (docstring) ...
        """
        async with self.get_session() as session:
            # --- FIX: Add 'await' here ---
            async with await session.begin_transaction() as tx: # <--- CORRECTED LINE
                for operation in batch:
                    query_template = operation['query']
                    items_list = operation['items']
                    if items_list:
                        full_query = f"UNWIND $items AS item\n{query_template}"
                        try:
                            # Run within the transaction 'tx'
                            await tx.run(full_query, items=items_list)
                        except Exception as e:
                            logger.error(f"Error in batch operation. Query template: {query_template}, Error: {e}", exc_info=True)
                            # Rollback the transaction on error
                            await tx.rollback() # Explicitly rollback
                            raise # Propagate error
                # Commit the transaction if loop completes without errors
                await tx.commit()


    async def update_repository_status(self, repo_url: str, commit_sha: str):
        """Updates the last indexed commit SHA for a repository."""
        query = """
        MERGE (r:Repository {url: $repo_url})
        SET r.last_indexed_commit_sha = $commit_sha, r.last_indexed_timestamp = timestamp()
        """
        parameters = {"repo_url": repo_url, "commit_sha": commit_sha}
        await self.run_query(query, parameters)


    # --- Vector Search Function (Placeholder for Phase 3 RAG Tool) ---
    async def vector_search_code_chunks(self, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """Performs vector similarity search on CodeChunk nodes."""
        # Assumes 'code_chunk_embeddings' index exists
        query = """
            CALL db.index.vector.queryNodes('code_chunk_embeddings', $k, $embedding)
            YIELD node, score
            RETURN node.text AS text, node.path AS path, node.start_line AS start_line, score
        """
        parameters = {"k": k, "embedding": query_embedding}
        logger.debug(f"Performing vector search with k={k}")
        try:
            async with self.get_session() as session:
                result = await session.run(query, parameters)
                records = await result.data()
                logger.debug(f"Vector search returned {len(records)} results.")
                return records
        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            return []

    async def query_high_level_info(self, topic: str, skip_faq: bool = False) -> List[Dict[str, Any]]:
        """
        Performs a specialized graph query to fetch high-level information directly from the database.
        
        Args:
            topic: The specific topic to query (e.g., "microservices", "architecture")
            skip_faq: Deprecated parameter, kept for backwards compatibility
            
        Returns:
            List of result dictionaries with text and path information
        """
        logger.info(f"Performing specialized high-level query for topic: {topic}")
        
        # No FAQ system - always query the database directly
        
        # Customize query based on topic
        if topic == "microservices" or topic == "services":
            # Query to find information about microservices or services
            # Prioritize chunks from README files and those with service descriptions
            query = """
            MATCH (cc:CodeChunk)
            WHERE (
                cc.text CONTAINS 'service' OR 
                cc.text CONTAINS 'microservice' OR
                cc.text CONTAINS 'architecture'
            )
            RETURN 
                cc.text AS text, 
                cc.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN cc.path CONTAINS 'README.md' THEN 2.0
                    WHEN cc.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
        elif topic == "architecture" or topic == "structure":
            # Query focused on architecture information
            query = """
            MATCH (cc:CodeChunk)
            WHERE (
                cc.text CONTAINS 'architect' OR 
                cc.text CONTAINS 'structure' OR
                cc.text CONTAINS 'diagram' OR
                cc.text CONTAINS 'workflow' OR
                cc.text CONTAINS 'design'
            )
            RETURN 
                cc.text AS text, 
                cc.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN cc.path CONTAINS 'README.md' THEN 2.0
                    WHEN cc.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
        elif topic == "overview" or topic == "about":
            # General project overview information
            query = """
            MATCH (cc:CodeChunk)
            WHERE (
                cc.path CONTAINS 'README.md' OR 
                cc.path CONTAINS '/docs/' OR
                cc.path ENDS WITH '.md'
            )
            RETURN 
                cc.text AS text, 
                cc.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN cc.path CONTAINS 'README.md' THEN 2.0
                    WHEN cc.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 10
            """
        else:
            # Generic topic search
            # Create a parameterized query that searches for the topic keyword
            query = """
            MATCH (cc:CodeChunk)
            WHERE 
                cc.text CONTAINS $topic
            RETURN 
                cc.text AS text, 
                cc.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN cc.path CONTAINS 'README.md' THEN 2.0
                    WHEN cc.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
            
        try:
            async with self.get_session() as session:
                # Pass topic parameter for the generic case
                parameters = {"topic": topic} if topic not in ["microservices", "services", "architecture", "structure", "overview", "about"] else {}
                result = await session.run(query, parameters)
                records = await result.data()
                logger.debug(f"Specialized query returned {len(records)} results for topic: {topic}")
                return records
        except Exception as e:
            logger.error(f"Error during specialized high-level query: {e}", exc_info=True)
            return []

    async def raw_cypher_query(self, cypher_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Executes a raw Cypher query for direct database inspection.
        This is primarily useful for testing and debugging.
        
        Args:
            cypher_query: The Cypher query to execute
            parameters: Optional parameters for the query
            
        Returns:
            The query results as a list of dictionaries
        """
        logger.info(f"Executing raw Cypher query: {cypher_query[:100]}...")
        try:
            async with self.get_session() as session:
                result = await session.run(cypher_query, parameters or {})
                records = await result.data()
                logger.debug(f"Raw Cypher query returned {len(records)} results.")
                return records
        except Exception as e:
            logger.error(f"Error during raw Cypher query: {e}", exc_info=True)
            raise

    async def knowledge_graph_query(self, query_type: str, keywords: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Advanced knowledge graph query that performs graph-based operations
        to extract structural information rather than just vector similarity.
        
        Args:
            query_type: Type of query to perform (services, relations, authors, dependencies)
            keywords: Optional list of keywords to filter results
            
        Returns:
            List of result dictionaries with the query results
        """
        logger.info(f"Executing knowledge graph query: {query_type}")
        
        try:
            # Build query based on type
            if query_type == "services":
                # Find all services in the system by analyzing code structure and relationships
                query = """
                MATCH (f:File)-[:CONTAINS]->(fn:Function)
                WHERE fn.name CONTAINS 'Service' OR fn.name CONTAINS 'service'
                   OR f.path CONTAINS 'service' OR f.path CONTAINS 'Service'
                WITH DISTINCT f.path AS service_file, collect(fn.name) AS functions
                RETURN service_file, functions, size(functions) AS function_count
                ORDER BY function_count DESC
                LIMIT 20
                """
                
            elif query_type == "dependencies":
                # Try to identify dependencies between components
                query = """
                MATCH (f1:File)-[:CONTAINS]->(cc1:CodeChunk)
                MATCH (f2:File)-[:CONTAINS]->(cc2:CodeChunk)
                WHERE f1 <> f2 
                   AND (cc1.text CONTAINS f2.path OR cc2.text CONTAINS f1.path)
                RETURN f1.path AS source, f2.path AS target, count(*) AS strength
                ORDER BY strength DESC
                LIMIT 25
                """
                
            elif query_type == "structure":
                # Analyze codebase structure
                query = """
                MATCH (r:Repository)<-[:BELONGS_TO]-(f:File)
                WITH r, f.language AS language, count(*) AS count
                ORDER BY count DESC
                RETURN r.url AS repository, 
                       collect({language: language, count: count}) AS language_breakdown,
                       sum(count) AS total_files
                """
                
            elif query_type == "interface_analysis":
                # Find interfaces and their implementations
                query = """
                MATCH (f:File)-[:CONTAINS]->(cl:Class)
                WHERE cl.name CONTAINS 'Interface' OR cl.name STARTS WITH 'I' AND size(cl.name) > 1
                RETURN f.path AS file, cl.name AS interface, cl.start_line AS line
                ORDER BY file
                LIMIT 20
                """
                
            else:
                # Default to a simple file-function relationship query
                query = """
                MATCH (f:File)-[:CONTAINS]->(fn:Function)
                WITH f.path AS file_path, count(fn) AS function_count
                WHERE function_count > 3
                RETURN file_path, function_count
                ORDER BY function_count DESC
                LIMIT 20
                """
                
            # Apply keyword filtering if provided
            if keywords and len(keywords) > 0:
                # This is a simplified approach - for production, you'd want to integrate this more carefully
                # into each specific query type
                keyword_conditions = " OR ".join([f"cc.text CONTAINS '{kw}'" for kw in keywords])
                query = f"""
                MATCH (f:File)-[:CONTAINS]->(cc:CodeChunk)
                WHERE {keyword_conditions}
                WITH DISTINCT f
                {query}
                """
                
            async with self.get_session() as session:
                result = await session.run(query)
                records = await result.data()
                logger.debug(f"Knowledge graph query returned {len(records)} results.")
                return records
                
        except Exception as e:
            logger.error(f"Error during knowledge graph query: {e}", exc_info=True)
            return []


# Instantiate the manager for use in ingestion and the main app
db_manager = Neo4jManager(
    uri=settings.neo4j_uri,
    user=settings.neo4j_username,
    password=settings.neo4j_password
)