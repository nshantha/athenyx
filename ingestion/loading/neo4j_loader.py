# ingestion/loading/neo4j_loader.py
import logging
import os
from typing import List, Dict, Any
from app.db.neo4j_manager import db_manager # Use the instantiated manager
from ingestion.config import ingestion_settings

logger = logging.getLogger(__name__)

class Neo4jLoader:

    def __init__(self, repo_url: str):
        self.repo_url = repo_url

    async def load_data(self, parsed_data: List[Dict[str, Any]], chunks_with_embeddings: List[Dict[str, Any]]):
        """
        Loads parsed structural data and embedded chunks into Neo4j using batching.
        """
        logger.info(f"Starting Neo4j loading for repository: {self.repo_url}")

        # Prepare batches for nodes and relationships
        # Use the batch_merge_nodes_relationships function in db_manager

        batch_size = ingestion_settings.neo4j_batch_size
        all_operations = [] # List to hold batches of operations

        # --- 1. Prepare Repository Node Operation ---
        repo_op = {
            'query': "MERGE (r:Repository {url: item.url}) SET r.name = item.name",
            'items': [{"url": self.repo_url, "name": self.repo_url.split('/')[-1].replace('.git', '')}]
        }
        all_operations.append(repo_op)


        # --- 2. Prepare File Nodes and Relationships ---
        file_items = []
        for file_data in parsed_data:
             if not file_data.get('parse_error'):
                file_path = file_data['path']
                file_items.append({
                    "path": file_path,
                    "props": {
                        "name": os.path.basename(file_path),
                        "language": file_data.get("language", "unknown"), # Assuming language is added during parsing prep
                    },
                    "repo_url": self.repo_url
                })

        if file_items:
            # MERGE File node and set properties
            file_node_query = """
            MERGE (f:File {path: item.path})
            SET f += item.props
            WITH f, item
            MATCH (r:Repository {url: item.repo_url}) // Match the repo node
            MERGE (f)-[:BELONGS_TO]->(r) // Create relationship
            """
            # Process in batches
            for i in range(0, len(file_items), batch_size):
                 all_operations.append({'query': file_node_query, 'items': file_items[i:i+batch_size]})


        # --- 3. Prepare Function/Class Nodes and Relationships ---
        func_items = []
        class_items = []
        for file_data in parsed_data:
             if not file_data.get('parse_error'):
                 file_path = file_data['path']
                 for func in file_data.get('functions', []):
                     func_items.append({
                         "unique_id": func['unique_id'],
                         "props": {
                             "name": func['name'],
                             "start_line": func['start_line'],
                             "end_line": func['end_line'],
                             # Add other relevant props, maybe size?
                         },
                         "file_path": file_path
                     })
                 for cls in file_data.get('classes', []):
                     class_items.append({
                         "unique_id": cls['unique_id'],
                         "props": {
                             "name": cls['name'],
                             "start_line": cls['start_line'],
                             "end_line": cls['end_line'],
                         },
                         "file_path": file_path
                     })

        # Function Nodes and CONTAINS Relationship
        if func_items:
            func_node_query = """
            MERGE (fn:Function {unique_id: item.unique_id})
            SET fn += item.props
            WITH fn, item
            MATCH (f:File {path: item.file_path}) // Match the parent file
            MERGE (f)-[:CONTAINS]->(fn) // Create relationship
            """
            for i in range(0, len(func_items), batch_size):
                all_operations.append({'query': func_node_query, 'items': func_items[i:i+batch_size]})

        # Class Nodes and CONTAINS Relationship
        if class_items:
            class_node_query = """
            MERGE (cl:Class {unique_id: item.unique_id})
            SET cl += item.props
            WITH cl, item
            MATCH (f:File {path: item.file_path}) // Match the parent file
            MERGE (f)-[:CONTAINS]->(cl) // Create relationship
            """
            for i in range(0, len(class_items), batch_size):
                 all_operations.append({'query': class_node_query, 'items': class_items[i:i+batch_size]})


        # --- 4. Prepare CodeChunk Nodes and Relationships ---
        chunk_items = []
        for chunk in chunks_with_embeddings:
             # Ensure embedding exists before adding
             if 'embedding' in chunk:
                # Remove embedding from props to avoid storing it directly on node properties
                props = {k: v for k, v in chunk.items() if k != 'embedding'}
                chunk_items.append({
                    "chunk_id": chunk['chunk_id'],
                    "embedding": chunk['embedding'], # Embedding passed separately for index
                    "props": props,
                    "parent_id": chunk['parent_id'] # ID of the File, Function, or Class node
                })

        if chunk_items:
            chunk_node_query = """
            MERGE (cc:CodeChunk {chunk_id: item.chunk_id})
            // Set properties INCLUDING the embedding for the vector index
            SET cc = item.props
            SET cc.embedding = item.embedding
            WITH cc, item
            // Match the parent node (File, Function, or Class)
            // We need to match based on the type encoded in parent_id or have separate queries
            // Simple approach: Try matching all possible parents using unique_id/path
            MATCH (parent) WHERE parent.unique_id = item.parent_id OR parent.path = item.parent_id
            MERGE (parent)-[:CONTAINS_CHUNK]->(cc)
            """
            for i in range(0, len(chunk_items), batch_size):
                 all_operations.append({'query': chunk_node_query, 'items': chunk_items[i:i+batch_size]})

        # --- Execute all batched operations ---
        logger.info(f"Executing {len(all_operations)} batch operations in Neo4j...")
        try:
            # The db_manager function handles transactions internally per batch list
            await db_manager.batch_merge_nodes_relationships(all_operations)
            logger.info("Successfully loaded data into Neo4j.")
        except Exception as e:
            logger.error(f"Failed during Neo4j batch loading: {e}", exc_info=True)
            # Consider adding cleanup logic here if needed
            raise # Propagate error