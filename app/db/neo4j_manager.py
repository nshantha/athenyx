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


# Instantiate the manager for use in ingestion and the main app
db_manager = Neo4jManager(
    uri=settings.neo4j_uri,
    user=settings.neo4j_username,
    password=settings.neo4j_password
)