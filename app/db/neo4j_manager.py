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

    def is_connected(self) -> bool:
        """Checks if the Neo4j connection is established."""
        return self._driver is not None

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
            # Core entity constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.url IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE", # Unique within the repo context ideally, simple approach first
            "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE fn.unique_id IS UNIQUE", # Requires generating a unique ID
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Class) REQUIRE cl.unique_id IS UNIQUE", # Requires generating a unique ID
            "CREATE CONSTRAINT IF NOT EXISTS FOR (cc:CodeChunk) REQUIRE cc.chunk_id IS UNIQUE", # Requires generating a unique ID
            
            # Service-related constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (api:ApiEndpoint) REQUIRE (api.name, api.repo_url) IS NODE KEY",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (dm:DataModel) REQUIRE (dm.name, dm.repo_url) IS NODE KEY",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (si:ServiceInterface) REQUIRE si.name IS UNIQUE",
        ]
        
        # Create indexes for frequently queried properties
        index_queries = [
            "CREATE INDEX service_name_idx IF NOT EXISTS FOR (s:Service) ON (s.name)",
            "CREATE INDEX repo_url_idx IF NOT EXISTS FOR (r:Repository) ON (r.url)",
            "CREATE INDEX file_path_idx IF NOT EXISTS FOR (f:File) ON (f.path)",
            "CREATE INDEX function_name_idx IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
            "CREATE INDEX class_name_idx IF NOT EXISTS FOR (cl:Class) ON (cl.name)",
            "CREATE INDEX api_path_idx IF NOT EXISTS FOR (api:ApiEndpoint) ON (api.api_path)",
            "CREATE INDEX datamodel_name_idx IF NOT EXISTS FOR (dm:DataModel) ON (dm.name)",
        ]
        
        # Vector Index (adjust name and dimensions as needed)
        vector_index_query = f"""
        CREATE VECTOR INDEX code_chunk_embeddings IF NOT EXISTS
        FOR (c:CodeChunk) ON (c.embedding)
        OPTIONS {{ indexConfig: {{
            `vector.dimensions`: {dimensions},
            `vector.similarity_function`: 'cosine'
        }} }}
        """

        async with self.get_session() as session:
            # Create constraints
            for query in constraint_queries:
                try:
                    logger.debug(f"Running: {query}")
                    await session.run(query)
                except Exception as e:
                    logger.warning(f"Could not create constraint (may already exist): {e}")
            
            # Create indexes
            for query in index_queries:
                try:
                    logger.debug(f"Running: {query}")
                    await session.run(query)
                except Exception as e:
                    logger.warning(f"Could not create index (may already exist): {e}")
            
            # Create vector index
            try:
                logger.debug(f"Running: {vector_index_query}")
                await session.run(vector_index_query)
            except Exception as e:
                logger.warning(f"Could not create vector index: {e}")
                
        logger.info("Constraints and vector index check complete.")

    async def get_repository_status(self, repo_url: str) -> Optional[str]:
        """
        Get the last indexed commit SHA for a repository.
        
        Args:
            repo_url: URL of the repository
            
        Returns:
            Last indexed commit SHA or None if not indexed
        """
        query = """
        MATCH (r:Repository {url: $repo_url})
        RETURN r.last_indexed_commit_sha as commit_sha
        """
        
        try:
            result = await self.run_query(query, {"repo_url": repo_url})
            if result and len(result) > 0:
                return result[0].get("commit_sha")
            return None
        except Exception as e:
            logger.error(f"Error getting repository status: {e}", exc_info=True)
            return None

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
        
        Args:
            batch: List of operations, each containing a query template and items list
                  Format: [{'query': 'MERGE (n:Node) ...', 'items': [{...}, {...}]}]
                  
        Returns:
            None
        """
        async with self.get_session() as session:
            # --- FIX: Add 'await' here ---
            async with await session.begin_transaction() as tx: # <--- CORRECTED LINE
                for operation in batch:
                    query_template = operation['query']
                    items_list = operation['items']
                    
                    if not items_list:
                        logger.warning(f"Skipping empty items list for query: {query_template[:50]}...")
                        continue
                        
                    # Filter out any None values and ensure all items are valid dictionaries
                    filtered_items = []
                    for item in items_list:
                        if item is None:
                            logger.warning("Skipping None item in batch")
                            continue
                        # Ensure all values in the item are not None
                        clean_item = {k: v for k, v in item.items() if v is not None}
                        if clean_item:
                            filtered_items.append(clean_item)
                    
                    if not filtered_items:
                        logger.warning(f"All items were filtered out for query: {query_template[:50]}...")
                        continue
                        
                    full_query = f"UNWIND $items AS item\n{query_template}"
                    try:
                        # Run within the transaction 'tx'
                        await tx.run(full_query, items=filtered_items)
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
        SET r.last_indexed_commit_sha = $commit_sha, 
            r.last_indexed_timestamp = timestamp(),
            r.last_commit_hash = $commit_sha
        """
        parameters = {"repo_url": repo_url, "commit_sha": commit_sha}
        await self.run_query(query, parameters)


    # --- Vector Search Function (Placeholder for Phase 3 RAG Tool) ---
    async def vector_search_code_chunks(
        self, 
        query_embedding: List[float], 
        k: int = 10,
        repository_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs a vector similarity search in the Neo4j database.
        
        Args:
            query_embedding: The embedding vector of the query
            k: Number of results to return
            repository_url: Optional URL of the repository to search in
            
        Returns:
            List of dictionaries containing the search results
        """
        try:
            # First check if this is a project structure query
            # If so, prioritize README files and other documentation
            project_structure_keywords = ["structure", "architecture", "overview", "about", "project", "purpose"]
            query_str = " ".join([str(x) for x in query_embedding[:20]])  # Use part of the embedding for keyword check
            is_structure_query = any(keyword in query_str.lower() for keyword in project_structure_keywords)
            
            # If this is a project structure query, look for README files first
            if is_structure_query:
                logger.info("Detected project structure query, prioritizing README files")
                
                # Try to find README files first
                direct_readme_query = """
                MATCH (f:File)
                WHERE 
                    f.path CONTAINS 'README.md' OR 
                    f.path CONTAINS 'README' OR
                    f.is_documentation = true
                """
                
                if repository_url:
                    direct_readme_query += " AND f.repo_url = $repo_url"
                    
                direct_readme_query += """
                WITH f
                MATCH (f)-[:CONTAINS]->(cc:CodeChunk)
                WHERE cc.embedding IS NOT NULL
                RETURN cc.content AS text, 
                       f.path AS path, 
                       cc.start_line AS start_line, 
                       0.95 AS score  // High score for README files
                LIMIT $k
                """
                
                params = {"k": k}
                if repository_url:
                    params["repo_url"] = repository_url
                    
                async with self.get_session() as session:
                    result = await session.run(direct_readme_query, params)
                    records = await result.data()
                    
                    # If we found README files, return them
                    if records and len(records) > 0:
                        logger.info(f"Found {len(records)} README/documentation files for structure query")
                        return records
                    
                    # If not, continue with vector search but boost READMEs
            
            # Build the vector search query with optional repository filtering and README boosting
            if repository_url:
                query = """
                MATCH (cc:CodeChunk)
                MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
                WITH cc, f
                CALL db.index.vector.queryNodes('code_chunk_embeddings', $k, $query_embedding) 
                YIELD node, score WHERE node = cc
                WITH cc, f, score AS base_score
                WITH cc, f, base_score,
                     CASE 
                        WHEN f.path CONTAINS 'README.md' THEN base_score * 1.5
                        WHEN f.path CONTAINS 'README' THEN base_score * 1.4
                        WHEN f.is_documentation = true THEN base_score * 1.3
                        WHEN f.path CONTAINS '/docs/' THEN base_score * 1.2
                        ELSE base_score
                     END AS score
                WHERE score > 0.4  // Lower threshold to catch more potential matches
                
                RETURN cc.content AS text, 
                       f.path AS path, 
                       cc.start_line AS start_line, 
                       score
                ORDER BY score DESC
                LIMIT $k
                """
                params = {"query_embedding": query_embedding, "k": k, "repo_url": repository_url}
            else:
                query = """
                MATCH (cc:CodeChunk)
                MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
                WITH cc, f
                CALL db.index.vector.queryNodes('code_chunk_embeddings', $k, $query_embedding) 
                YIELD node, score WHERE node = cc
                WITH cc, f, score AS base_score
                WITH cc, f, base_score,
                     CASE 
                        WHEN f.path CONTAINS 'README.md' THEN base_score * 1.5
                        WHEN f.path CONTAINS 'README' THEN base_score * 1.4
                        WHEN f.is_documentation = true THEN base_score * 1.3
                        WHEN f.path CONTAINS '/docs/' THEN base_score * 1.2
                        ELSE base_score
                     END AS score
                WHERE score > 0.4  // Lower threshold to catch more potential matches
                
                RETURN cc.content AS text, 
                       f.path AS path, 
                       cc.start_line AS start_line, 
                       score
                ORDER BY score DESC
                LIMIT $k
                """
                params = {"query_embedding": query_embedding, "k": k}
                
            async with self.get_session() as session:
                result = await session.run(query, params)
                records = await result.data()
                logger.debug(f"Vector search returned {len(records)} results")
                return records
        except Exception as e:
            logger.error(f"Error during vector search: {e}", exc_info=True)
            return []

    async def query_high_level_info(self, topic: str, skip_faq: bool = False, repository_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Performs a specialized graph query to fetch high-level information directly from the database.
        
        Args:
            topic: The specific topic to query (e.g., "microservices", "architecture")
            skip_faq: Deprecated parameter, kept for backwards compatibility
            repository_url: Optional repository URL to limit query scope
            
        Returns:
            List of result dictionaries with text and path information
        """
        logger.info(f"Performing specialized high-level query for topic: {topic}")
                
        # Get active repository if none specified
        if not repository_url:
            active_repo = await self.get_active_repository()
            if active_repo:
                repository_url = active_repo.get('url')
                logger.info(f"Using active repository: {repository_url}")
        
        # Customize query based on topic
        if topic == "microservices" or topic == "services":
            # Query to find information about microservices or services
            # Prioritize chunks from README files and those with service descriptions
            query = """
            MATCH (cc:CodeChunk)
            WHERE (
                cc.content CONTAINS 'service' OR
                cc.content CONTAINS 'microservice' OR
                cc.content CONTAINS 'architecture'
            )
            MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN f.path CONTAINS 'README.md' THEN 2.0
                    WHEN f.path CONTAINS '/docs/' THEN 1.5
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
                cc.content CONTAINS 'architect' OR 
                cc.content CONTAINS 'structure' OR
                cc.content CONTAINS 'diagram' OR
                cc.content CONTAINS 'workflow' OR
                cc.content CONTAINS 'design'
            )
            MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN f.path CONTAINS 'README.md' THEN 2.0
                    WHEN f.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
        elif topic == "project_structure":
            # Enhanced query for project structure that uses multiple approaches
            query = """
            // First check README files directly without requiring keywords
            MATCH (f:File)
            WHERE f.path CONTAINS 'README.md' OR f.path ENDS WITH '/README' OR f.path ENDS WITH '/README.txt'
            WITH f
            MATCH (cc:CodeChunk)
            WHERE (f)-[:CONTAINS]->(cc)
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                4.0 AS priority
                
            UNION
                
            // Look for files in docs directory
            MATCH (f:File)
            WHERE f.path CONTAINS '/docs/' AND (f.path ENDS WITH '.md' OR f.path ENDS WITH '.txt')
            WITH f
            MATCH (cc:CodeChunk)
            WHERE (f)-[:CONTAINS]->(cc)
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                3.0 AS priority
                
            UNION
                
            // Analyze directory structure 
            MATCH (f:File)
            WITH split(f.path, '/') AS parts, count(*) AS file_count
            WHERE size(parts) > 1
            WITH parts[0] AS top_dir, count(*) AS file_count
            ORDER BY file_count DESC
            LIMIT 15
            RETURN 
                'Top-level directory: ' + top_dir + ' (contains ' + toString(file_count) + ' files)' AS text, 
                'directory_structure' AS path, 
                0 AS start_line,
                2.0 AS priority
                
            UNION
                
            // Find documentation with structure keywords
            MATCH (f:File)
            WHERE f.is_documentation = true OR f.path ENDS WITH '.md'
            WITH f
            MATCH (cc:CodeChunk)
            WHERE (f)-[:CONTAINS]->(cc)
            AND (
                cc.content CONTAINS 'project' OR
                cc.content CONTAINS 'structure' OR
                cc.content CONTAINS 'directory' OR
                cc.content CONTAINS 'folder' OR
                cc.content CONTAINS 'organization' OR
                cc.content CONTAINS 'layout'
            )
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                1.0 AS priority
            ORDER BY priority DESC
            LIMIT 30
            """
        elif topic == "overview" or topic == "about":
            # General project overview information
            query = """
            MATCH (cc:CodeChunk)
            MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
            WHERE (
                f.path CONTAINS 'README.md' OR 
                f.path CONTAINS '/docs/' OR
                f.path ENDS WITH '.md'
            )
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN f.path CONTAINS 'README.md' THEN 2.0
                    WHEN f.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
        else:
            # Generic topic search
            # Create a parameterized query that searches for the topic keyword
            query = """
            MATCH (cc:CodeChunk)
            WHERE 
                cc.content CONTAINS $topic
            MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
            RETURN 
                cc.content AS text, 
                f.path AS path, 
                cc.start_line AS start_line,
                CASE 
                    WHEN f.path CONTAINS 'README.md' THEN 2.0
                    WHEN f.path CONTAINS '/docs/' THEN 1.5
                    ELSE 1.0
                END AS priority
            ORDER BY priority DESC
            LIMIT 15
            """
            
        try:
            async with self.get_session() as session:
                # Pass topic parameter for the generic case
                parameters = {"topic": topic} if topic not in [
                    "microservices", "services", "architecture", 
                    "structure", "overview", "about", "project_structure"
                ] else {}
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
                MATCH (fn:Function)
                WHERE fn.name CONTAINS 'Service' OR fn.name CONTAINS 'service'
                WITH fn
                MATCH (f:File)-[:CONTAINS]->(fn)
                RETURN f.path AS service_file, collect(fn.name) AS functions, size(collect(fn.name)) AS function_count
                ORDER BY function_count DESC
                LIMIT 20
                """
                
            elif query_type == "dependencies":
                # Try to identify dependencies between components
                query = """
                MATCH (f1:File)
                MATCH (f2:File)
                WHERE f1 <> f2
                MATCH (cc1:CodeChunk) WHERE (f1)-[:CONTAINS]->(cc1)
                MATCH (cc2:CodeChunk) WHERE (f2)-[:CONTAINS]->(cc2)
                WHERE cc1.text CONTAINS f2.path OR cc2.text CONTAINS f1.path
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
                # Default to a simple file-function relationship query that uses the correct relationship type
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
                keyword_conditions = " OR ".join([f"cc.content CONTAINS '{kw}'" for kw in keywords])
                query = f"""
                MATCH (cc:CodeChunk)
                WHERE {keyword_conditions}
                WITH cc
                MATCH (f:File) WHERE (f)-[:CONTAINS]->(cc)
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

    async def get_all_repositories(self) -> List[Dict[str, Any]]:
        """
        Retrieves all repositories from the database with their metadata.
        
        Returns:
            List of dictionaries containing repository information
        """
        query = """
        MATCH (r:Repository)
        RETURN r.url as url, 
               r.service_name as service_name, 
               r.description as description,
               COALESCE(r.last_commit_hash, '') as last_commit,
               r.last_indexed_commit_sha as last_indexed
        ORDER BY r.url
        """
        try:
            results = await self.run_query(query)
            return results
        except Exception as e:
            logger.error(f"Error retrieving repositories: {e}", exc_info=True)
            return []
            
    async def set_active_repository(self, repo_url: str) -> bool:
        """
        Sets a repository as active/current for the application.
        This is useful for managing context in multi-repository environments.
        
        Args:
            repo_url: The URL of the repository to set as active
            
        Returns:
            Boolean indicating success
        """
        # First check if the repository exists
        check_query = """
        MATCH (r:Repository {url: $repo_url})
        RETURN r.url as url
        """
        
        try:
            result = await self.run_query(check_query, {"repo_url": repo_url})
            if not result or len(result) == 0:
                logger.warning(f"Repository not found: {repo_url}")
                return False
                
            # Now reset all repositories' active status and set the specified one
            update_query = """
            // First reset all repositories by removing the property
            MATCH (r:Repository)
            REMOVE r.is_active
            
            // Then set the specified repository as active
            WITH count(*) as _
            MATCH (target:Repository {url: $repo_url})
            SET target.is_active = true
            RETURN target.url as url, target.service_name as service_name
            """
            
            params = {"repo_url": repo_url}
            result = await self.run_query(update_query, params)
            success = len(result) > 0
            
            if success:
                logger.info(f"Set active repository to: {repo_url}")
            else:
                logger.warning(f"Failed to set active repository - repository not found: {repo_url}")
            return success
        except Exception as e:
            logger.error(f"Error setting active repository: {e}", exc_info=True)
            return False
            
    async def get_active_repository(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the currently active repository.
        
        Returns:
            Dictionary with active repository information or None if no active repository
        """
        query = """
        MATCH (r:Repository)
        WHERE r.is_active = true
        RETURN r.url as url, 
               r.service_name as service_name, 
               r.description as description,
               COALESCE(r.last_commit_hash, '') as last_commit,
               r.last_indexed_commit_sha as last_indexed
        """
        
        try:
            results = await self.run_query(query)
            if results and len(results) > 0:
                return results[0]
                
            # If no active repository found, try to get any repository
            fallback_query = """
            MATCH (r:Repository)
            RETURN r.url as url, 
                  r.service_name as service_name, 
                  r.description as description,
                  COALESCE(r.last_commit_hash, '') as last_commit,
                  r.last_indexed_commit_sha as last_indexed
            LIMIT 1
            """
            
            fallback_results = await self.run_query(fallback_query)
            if fallback_results and len(fallback_results) > 0:
                # Set this as active for consistency
                await self.set_active_repository(fallback_results[0]['url'])
                return fallback_results[0]
                
            return None
        except Exception as e:
            logger.error(f"Error retrieving active repository: {e}", exc_info=True)
            return None

    async def get_connected_repositories(self, repo_url: str) -> List[Dict[str, Any]]:
        """
        Finds repositories that are connected to the given repository through relationships.
        
        Args:
            repo_url: URL of the repository to find connections for
            
        Returns:
            List of dictionaries containing connected repository information
        """
        query = """
        // Find repositories connected through API calls
        MATCH (r1:Repository {url: $repo_url})<-[:BELONGS_TO]-(:ApiEndpoint)<-[:MAY_CALL]-(:Function)-[:BELONGS_TO]->(r2:Repository)
        WHERE r1 <> r2
        RETURN DISTINCT r2.url as url, 
               r2.service_name as service_name, 
               r2.description as description,
               null as last_commit,
               null as last_indexed
        
        UNION
        
        // Union with repositories connected through shared data models
        MATCH (r1:Repository {url: $repo_url})<-[:BELONGS_TO]-(:DataModel)-[:SIMILAR_TO]-(:DataModel)-[:BELONGS_TO]->(r2:Repository)
        WHERE r1 <> r2
        RETURN DISTINCT r2.url as url, 
               r2.service_name as service_name, 
               r2.description as description,
               null as last_commit,
               null as last_indexed
        
        UNION
        
        // Union with repositories connected through API model usage
        MATCH (r1:Repository {url: $repo_url})<-[:BELONGS_TO]-(:ApiEndpoint)-[:USES_MODEL]->(:DataModel)-[:BELONGS_TO]->(r2:Repository)
        WHERE r1 <> r2
        RETURN DISTINCT r2.url as url, 
               r2.service_name as service_name, 
               r2.description as description,
               null as last_commit,
               null as last_indexed
        """
        
        try:
            params = {"repo_url": repo_url}
            results = await self.run_query(query, params)
            return results
        except Exception as e:
            logger.error(f"Error retrieving connected repositories: {e}", exc_info=True)
            return []

    async def get_repository_connections_summary(self, repo_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Gets a summary of all repository connections in the system.
        If repo_url is provided, only returns connections for that repository.
        
        Args:
            repo_url: Optional URL of the repository to get connections for
            
        Returns:
            List of dictionaries containing connection information
        """
        try:
            if repo_url:
                # Query for specific repository connections
                query = """
                MATCH (r1:Repository {url: $repo_url})-[rel]->(r2:Repository)
                RETURN r1.url as source_url, 
                       r1.service_name as source_name,
                       r2.url as target_url,
                       r2.service_name as target_name,
                       type(rel) as connection_type,
                       1 as strength,
                       type(rel) as connection_description
                """
                params = {"repo_url": repo_url}
            else:
                # Query for all repository connections
                query = """
                MATCH (r1:Repository)-[rel]->(r2:Repository)
                RETURN r1.url as source_url, 
                       r1.service_name as source_name,
                       r2.url as target_url,
                       r2.service_name as target_name,
                       type(rel) as connection_type,
                       1 as strength,
                       type(rel) as connection_description
                """
                params = {}
                
            results = await self.run_query(query, params)
            return results
        except Exception as e:
            logger.error(f"Error retrieving repository connections: {e}", exc_info=True)
            return []
            
    async def get_repository_connection_details(self, source_url: str, target_url: str) -> Dict[str, Any]:
        """
        Gets detailed information about the connection between two repositories.
        
        Args:
            source_url: URL of the source repository
            target_url: URL of the target repository
            
        Returns:
            Dictionary containing detailed connection information
        """
        try:
            # Query for connection details
            query = """
            // Get basic connection information
            MATCH (r1:Repository {url: $source_url})-[rel]->(r2:Repository {url: $target_url})
            
            // Get API calls between repositories
            OPTIONAL MATCH (func:Function)-[:BELONGS_TO]->(r1)
            OPTIONAL MATCH (api:ApiEndpoint)-[:BELONGS_TO]->(r2)
            OPTIONAL MATCH (func)-[:MAY_CALL]->(api)
            WITH r1, r2, rel, collect({function: func.name, api: api.name, path: api.api_path}) as api_calls
            
            // Get shared data models
            OPTIONAL MATCH (dm1:DataModel)-[:BELONGS_TO]->(r1)
            OPTIONAL MATCH (dm2:DataModel)-[:BELONGS_TO]->(r2)
            OPTIONAL MATCH (dm1)-[:SIMILAR_TO]->(dm2)
            WITH r1, r2, rel, api_calls, collect({model1: dm1.name, model2: dm2.name}) as shared_models
            
            // Return detailed connection information
            RETURN r1.service_name as source_name,
                   r2.service_name as target_name,
                   type(rel) as connection_type,
                   1 as strength,
                   api_calls,
                   shared_models,
                   null as first_detected,
                   null as last_updated
            """
            
            params = {"source_url": source_url, "target_url": target_url}
            
            results = await self.run_query(query, params)
            if results and len(results) > 0:
                return results[0]
            return {}
        except Exception as e:
            logger.error(f"Error retrieving repository connection details: {e}", exc_info=True)
            return {}


# Instantiate the manager for use in ingestion and the main app
db_manager = Neo4jManager(
    uri=settings.neo4j_uri,
    user=settings.neo4j_username,
    password=settings.neo4j_password
)