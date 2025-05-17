# ingestion/loading/neo4j_loader.py
import logging
import os
from typing import List, Dict, Any
from app.db.neo4j_manager import db_manager # Use the instantiated manager
from ingestion.config import ingestion_settings
import uuid
import hashlib

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class Neo4jLoader:

    def __init__(self, repo_url: str):
        self.repo_url = repo_url

    def _normalize_path(self, path: str, repo_url: str) -> str:
        """
        Normalize path by removing duplicate repository name prefix.
        
        Args:
            path: The file path to normalize
            repo_url: Repository URL to extract repo name from
            
        Returns:
            Normalized path
        """
        if not path:
            return path
            
        repo_name = ingestion_settings.extract_repo_name(repo_url)
        if path.startswith(f"{repo_name}/"):
            return path[len(repo_name)+1:]
        
        return path

    async def load_data(self, parsed_data: List[Dict[str, Any]], chunks_with_embeddings: List[Dict[str, Any]]):
        """
        Load parsed data and code chunks into Neo4j.
        
        Args:
            parsed_data: List of parsed file data
            chunks_with_embeddings: List of code chunks with embeddings
        """
        if not parsed_data:
            logger.warning("No parsed data to load.")
            return
            
        logger.info(f"Loading data for repository {self.repo_url}")
        
        try:
            # Ensure a connection to the database
            if not db_manager.is_connected():
                logger.info("Connecting to Neo4j database")
                await db_manager.connect()
                    
            # Extract repository name from the URL for better tracking
            repo_name = self.repo_url.split('/')[-1].replace('.git', '')
            
            # Determine service name (default to repository name without extension)
            service_name = repo_name.replace('.git', '')
            
            # Create Repository node
            logger.info(f"Creating repository node for {self.repo_url}")
            await self._create_repository_node(self.repo_url, repo_name, service_name)
            
            # Create Service node (if needed for the domain model)
            logger.info(f"Creating service node for {service_name}")
            await self._create_service_node(service_name, f"Service for {repo_name}", self.repo_url)
            
            # Process files
            logger.info(f"Processing {len(parsed_data)} files")
            for file_data in parsed_data:
                # Skip empty files
                if not file_data:
                    continue
                    
                # Process the file and create nodes
                file_node = await self._process_file(file_data)
                if not file_node:
                    continue
                
                # Special handling for READMEs (ensure they are chunked for RAG)
                file_path = file_data.get('path', '')
                if file_data.get('is_documentation', False) or file_path.lower().endswith('.md'):
                    await self._ensure_readme_chunks(file_path, self.repo_url, service_name)
            
            # Scan for README files that might not have been captured by the parser
            await self._scan_for_readme_files(self.repo_url, service_name)
                    
            # Process chunks with embeddings
            logger.info(f"Processing {len(chunks_with_embeddings)} code chunks with embeddings")
            for chunk_data in chunks_with_embeddings:
                # Skip empty chunks
                if not chunk_data:
                    continue
                
                # Process the chunk and create nodes
                await self._create_code_chunk_node(
                    chunk_id=chunk_data.get('chunk_id', ''),
                    content=chunk_data.get('content', ''),
                    start_line=chunk_data.get('start_line', 0),
                    end_line=chunk_data.get('end_line', 0),
                    parent_id=chunk_data.get('parent_id', ''),
                    embedding=chunk_data.get('embedding', []),
                    repo_url=self.repo_url,
                    service_name=service_name
                )
                
            logger.info(f"Successfully loaded data for repository {self.repo_url}")
        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            raise
        finally:
            # Leave the connection open for better performance in the overall process
            # Will be closed by the caller
            pass

    async def _create_repository_node(self, url: str, name: str, service_name: str):
        """Create a Repository node"""
        query = """
        MERGE (r:Repository {url: $url}) 
        SET r.name = $name,
            r.service_name = $service_name
        RETURN r
        """
        params = {"url": url, "name": name, "service_name": service_name}
        try:
            await db_manager.run_query(query, params)
            logger.info(f"Created Repository node: {name}")
        except Exception as e:
            logger.error(f"Error creating Repository node: {e}")
            raise

    async def _create_service_node(self, name: str, description: str, repo_url: str):
        """Create a Service node and link to Repository"""
        query = """
        MATCH (r:Repository {url: $repo_url})
        MERGE (s:Service {name: $name})
        SET s.description = $description,
            s.repository_url = $repo_url
        MERGE (s)-[:BELONGS_TO]->(r)
        RETURN s
        """
        params = {"name": name, "description": f"Service extracted from {description}", "repo_url": repo_url}
        try:
            await db_manager.run_query(query, params)
            logger.info(f"Created Service node: {name}")
        except Exception as e:
            logger.error(f"Error creating Service node: {e}")
            raise

    async def _create_file_node(self, path: str, name: str, language: str, file_type: str, repo_url: str, service_name: str):
        """Create a File node and link to Repository and Service"""
        # Normalize path to prevent duplicate repository name
        path = self._normalize_path(path, repo_url)
            
        query = """
        MERGE (f:File {path: $path})
        SET f.name = $name,
            f.language = $language,
            f.file_type = $file_type,
            f.repo_url = $repo_url,
            f.service_name = $service_name,
            f.is_documentation = $is_documentation
        WITH f
        MATCH (r:Repository {url: $repo_url})
        MATCH (s:Service {name: $service_name})
        MERGE (f)-[:BELONGS_TO]->(r)
        MERGE (f)-[:BELONGS_TO]->(s)
        RETURN f
        """
        
        # Mark documentation files (README, markdown, etc.)
        is_documentation = (
            "README" in path.upper() or 
            file_type.lower() in ["md", "markdown", "txt", "rst", "adoc"] or
            "/docs/" in path or
            "/documentation/" in path
        )
        
        params = {
            "path": path,
            "name": name,
            "language": language,
            "file_type": file_type,
            "repo_url": repo_url,
            "service_name": service_name,
            "is_documentation": is_documentation
        }
        try:
            await db_manager.run_query(query, params)
            # Log README files specifically since they're important
            if "README" in path.upper():
                logger.info(f"Created File node for README: {path}")
                
                # For README files, create direct text chunks if not already created by the parser
                # This ensures README content is always indexed regardless of parser limitations
                if name.upper() == "README.MD" or name.upper() == "README":
                    await self._ensure_readme_chunks(path, repo_url, service_name)
        except Exception as e:
            logger.error(f"Error creating File node for {path}: {e}")
            # Continue processing other files
            
    async def _ensure_readme_chunks(self, path: str, repo_url: str, service_name: str):
        """Ensure README files are properly chunked and indexed, even if parser doesn't handle them well"""
        try:
            # Extract repo name from the repo_url using the config utility
            repo_name = ingestion_settings.extract_repo_name(repo_url)
            
            # Normalize path
            path = self._normalize_path(path, repo_url)
            
            # The repository is cloned at ingestion_settings.clone_dir
            repo_root = os.path.join(ingestion_settings.clone_dir, repo_name)
            
            # Use the repo_root with the file path
            full_path = os.path.join(repo_root, path)
            logger.info(f"Looking for README file at {full_path}")
            
            if not os.path.exists(full_path):
                logger.warning(f"README file not found at {full_path}")
                return False
                
            # Check if we already have chunks for this README
            check_query = """
            MATCH (f:File {path: $path, repo_url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
            RETURN count(cc) as chunk_count
            """
            check_params = {"path": path, "repo_url": repo_url}
            check_result = await db_manager.run_query(check_query, check_params)
            
            if check_result and check_result[0]["chunk_count"] > 0:
                logger.info(f"README {path} already has {check_result[0]['chunk_count']} chunks")
                return True
            
            # Read the file
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            if not content.strip():
                logger.warning(f"README file {path} is empty")
                return False
                
            # Create chunks (simple paragraph-based for markdown)
            from langchain_text_splitters import MarkdownTextSplitter
            splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = splitter.split_text(content)
            
            # Create chunk nodes directly
            logger.info(f"Creating {len(chunks)} chunks for README {path}")
            
            for i, chunk_text in enumerate(chunks):
                chunk_id = f"readme::{repo_name}::{path}::{i}"
                
                # Create embedding for the chunk
                from ingestion.processing.embedding import generate_embedding
                embedding = await generate_embedding(chunk_text)
                
                # Estimate line range
                start_line = i * 10  # Approximate, not accurate but helps with sorting
                end_line = start_line + chunk_text.count('\n') + 1
                
                # Create the chunk node
                create_query = """
                MERGE (cc:CodeChunk {chunk_id: $chunk_id})
                SET cc.text = $content,
                    cc.start_line = $start_line,
                    cc.end_line = $end_line,
                    cc.repo_url = $repo_url,
                    cc.service_name = $service_name,
                    cc.embedding = $embedding,
                    cc.parent_type = 'File',
                    cc.is_readme = true
                WITH cc
                MATCH (f:File {path: $path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(cc)
                """
                
                create_params = {
                    "chunk_id": chunk_id,
                    "content": chunk_text,
                    "start_line": start_line,
                    "end_line": end_line,
                    "repo_url": repo_url,
                    "service_name": service_name,
                    "embedding": embedding,
                    "path": path
                }
                
                await db_manager.run_query(create_query, create_params)
                
            logger.info(f"Successfully created README chunks for {path}")
            return True
        except Exception as e:
            logger.error(f"Error ensuring README chunks for {path}: {e}", exc_info=True)
            return False

    async def _scan_for_readme_files(self, repo_url: str, service_name: str):
        """Scan for README files in the repository and ensure they are properly chunked"""
        try:
            # Extract repo name from the repo_url
            repo_name = ingestion_settings.extract_repo_name(repo_url)
            
            # The repository is cloned at ingestion_settings.clone_dir
            repo_root = os.path.join(ingestion_settings.clone_dir, repo_name)
            
            if not os.path.exists(repo_root):
                logger.warning(f"Repository directory not found at {repo_root}")
                return
            
            # Find all README files in the repository
            readme_files = []
            for root, _, files in os.walk(repo_root):
                for file in files:
                    if file.lower() in ["readme.md", "readme.txt", "readme"]:
                        abs_path = os.path.join(root, file)
                        # Convert absolute path to relative path within the repo
                        rel_path = os.path.relpath(abs_path, repo_root)
                        readme_files.append(rel_path)
            
            logger.warning(f"Found {len(readme_files)} README files in repository {repo_name}")
            
            # Process each README file
            for readme_path in readme_files:
                # Create a File node for the README if it doesn't exist
                readme_name = os.path.basename(readme_path)
                await self._create_file_node(
                    path=readme_path,  # This will be normalized in _create_file_node
                    name=readme_name,
                    language="markdown",
                    file_type="documentation",
                    repo_url=repo_url,
                    service_name=service_name
                )
                
                # Create chunks for the README
                await self._ensure_readme_chunks(readme_path, repo_url, service_name)
        
        except Exception as e:
            logger.error(f"Error scanning for README files: {e}", exc_info=True)

    async def _create_function_node(self, unique_id: str, name: str, start_line: int, end_line: int, 
                                   file_path: str, repo_url: str, service_name: str):
        """Create a Function node and link to File and Service"""
        # Check if this is a protobuf file
        is_protobuf = file_path.endswith('.proto')

        query = """
        MERGE (fn:Function {unique_id: $unique_id})
        SET fn.name = $name,
            fn.start_line = $start_line,
            fn.end_line = $end_line,
            fn.repo_url = $repo_url,
            fn.service_name = $service_name,
            fn.file_path = $file_path
        WITH fn
        MATCH (s:Service {name: $service_name})
        MERGE (fn)-[:BELONGS_TO]->(s)
        RETURN fn
        """
        params = {
            "unique_id": unique_id,
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
            "file_path": file_path,
            "repo_url": repo_url,
            "service_name": service_name
        }
        try:
            await db_manager.run_query(query, params)
            
            # Ensure the Function is connected to its parent File
            if is_protobuf:
                # For protobuf files, find all instances of this file and connect to all of them
                proto_files = await self._find_all_proto_file_paths(file_path, repo_url)
                
                for proto_path in proto_files:
                    # First ensure the file node exists
                    await self._ensure_file_node_exists(proto_path, repo_url, service_name)
                    
                    # Then connect the function to it
                    link_query = """
                    MATCH (fn:Function {unique_id: $unique_id, repo_url: $repo_url})
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MERGE (f)-[:CONTAINS]->(fn)
                    """
                    
                    await db_manager.run_query(link_query, {
                        "unique_id": unique_id,
                        "file_path": proto_path,
                        "repo_url": repo_url
                    })
            else:
                # Regular files - just connect to the file directly
                link_query = """
                MATCH (fn:Function {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (f:File {path: $file_path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(fn)
                """
                await db_manager.run_query(link_query, {
                    "unique_id": unique_id,
                    "file_path": file_path,
                    "repo_url": repo_url
                })
            
            # Don't log every function to avoid spamming logs
        except Exception as e:
            logger.error(f"Error creating Function node for {name}: {e}")
            # Continue processing other functions

    async def _create_class_node(self, unique_id: str, name: str, start_line: int, end_line: int, 
                                file_path: str, repo_url: str, service_name: str, is_data_model=False, is_api=False):
        """Create a Class node and link to File and Service"""
        # Check if this is a protobuf file
        is_protobuf = file_path.endswith('.proto')
        
        # Set class type and framework
        class_type = "class"
        framework = "Unknown"
        
        # Detect protobuf messages and services based on file extension and name patterns
        if is_protobuf:
            if is_api or "service" in unique_id.lower():
                is_api = True
                class_type = "service"
                framework = "gRPC"
            elif is_data_model or "message" in unique_id.lower():
                is_data_model = True
                class_type = "message"
        
        query = """
        MERGE (cl:Class {unique_id: $unique_id})
        SET cl.name = $name,
            cl.start_line = $start_line,
            cl.end_line = $end_line,
            cl.repo_url = $repo_url,
            cl.service_name = $service_name,
            cl.file_path = $file_path,
            cl.is_data_model = $is_data_model,
            cl.is_api = $is_api,
            cl.type = $class_type,
            cl.framework = $framework
        WITH cl
        MATCH (s:Service {name: $service_name})
        MERGE (cl)-[:BELONGS_TO]->(s)
        RETURN cl
        """
        params = {
            "unique_id": unique_id,
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
            "file_path": file_path,
            "repo_url": repo_url,
            "service_name": service_name,
            "is_data_model": is_data_model,
            "is_api": is_api,
            "class_type": class_type,
            "framework": framework
        }
        try:
            await db_manager.run_query(query, params)
            
            # Ensure the Class is connected to its parent File
            if is_protobuf:
                # For protobuf files, find all instances of this file and connect to all of them
                proto_files = await self._find_all_proto_file_paths(file_path, repo_url)
                
                for proto_path in proto_files:
                    # First ensure the file node exists
                    await self._ensure_file_node_exists(proto_path, repo_url, service_name)
                    
                    # Then connect the class to it
                    link_query = """
                    MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MERGE (f)-[:CONTAINS]->(cl)
                    """
                    
                    await db_manager.run_query(link_query, {
                        "unique_id": unique_id,
                        "file_path": proto_path,
                        "repo_url": repo_url
                    })
            else:
                # Regular files - just connect to the file directly
                link_query = """
                MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (f:File {path: $file_path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(cl)
                """
                await db_manager.run_query(link_query, {
                    "unique_id": unique_id,
                    "file_path": file_path,
                    "repo_url": repo_url
                })
            
            # Log only for special classes
            if is_data_model:
                logger.info(f"Created DataModel node for {name} in {file_path}")
            elif is_api:
                logger.info(f"Created ApiEndpoint node for {name} in {file_path}")
        except Exception as e:
            logger.error(f"Error creating Class node for {name}: {e}")
            # Continue processing other classes

    async def _create_code_chunk_node(self, chunk_id: str, content: str, start_line: int, end_line: int,
                                    parent_id: str, embedding: List[float], repo_url: str, service_name: str):
        """Create a CodeChunk node and link to parent (File, Function, or Class) and Service"""
        
        # Extract file path from parent_id for file-level chunks
        original_file_path = parent_id.replace("file::", "") if parent_id.startswith("file::") else ""
        file_path = original_file_path
        
        # Check if this is a protobuf file and handle specially
        is_protobuf = file_path.endswith('.proto')
        
        # Determine parent type from parent_id or chunk metadata
        if parent_id.startswith("file::"):
            # Check for class/function pattern in parent_id
            if "::class::" in parent_id.lower():
                parent_type = "Class"
            elif "::function::" in parent_id.lower():
                parent_type = "Function"
            else:
                # If not a class or function, it's a file-level chunk
                parent_type = "File"
        elif "::class::" in parent_id.lower() or any(class_marker in chunk_id.lower() for class_marker in ["_class_", "::class"]):
            parent_type = "Class"
        elif "::function::" in parent_id.lower() or any(func_marker in chunk_id.lower() for func_marker in ["_function_", "::func"]):
            parent_type = "Function"
        else:
            # Default to the most common pattern from TreeSitterParser
            # Check if parent_id contains double-colon and make a reasonable guess
            if "::" in parent_id:
                parts = parent_id.split("::")
                if len(parts) > 1:
                    # If the second part is PascalCase, it's likely a class
                    second_part = parts[1]
                    if second_part and second_part[0].isupper():
                        parent_type = "Class"
                    else:
                        parent_type = "Function"
                else:
                    parent_type = "File"  # Default to File if we can't determine
            else:
                parent_type = "File"  # Default to File
        
        # Create CodeChunk node
        create_query = """
        MERGE (cc:CodeChunk {chunk_id: $chunk_id})
        SET cc.content = $content,
            cc.start_line = $start_line,
            cc.end_line = $end_line,
            cc.repo_url = $repo_url,
            cc.service_name = $service_name,
            cc.embedding = $embedding,
            cc.parent_type = $parent_type,
            cc.file_path = $file_path,
            cc.parent_id = $parent_id
        RETURN cc
        """
        
        create_params = {
            "chunk_id": chunk_id,
            "content": content,
            "start_line": start_line,
            "end_line": end_line,
            "repo_url": repo_url,
            "service_name": service_name,
            "embedding": embedding,
            "parent_type": parent_type,
            "file_path": file_path,
            "parent_id": parent_id
        }
        
        success = False
        
        try:
            await db_manager.run_query(create_query, create_params)
            
            # For protobuf files, ensure we have the file node first
            if is_protobuf:
                # Check if file node exists and create if it doesn't
                await self._ensure_file_node_exists(file_path, repo_url, service_name)
            
            # Connect to parent entity based on type
            if parent_type == "Class":
                # Try to find by unique_id first
                class_query = """
                MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                MERGE (cl)-[:CONTAINS]->(cc)
                RETURN cl
                """
                
                class_params = {
                    "unique_id": parent_id,
                    "chunk_id": chunk_id,
                    "repo_url": repo_url
                }
                
                class_result = await db_manager.run_query(class_query, class_params)
                
                # If no class found by unique_id, try to find by line range
                if not class_result or len(class_result) == 0:
                    # Try to find a class that contains this chunk's line range
                    find_class_query = """
                    MATCH (cl:Class)
                    WHERE cl.file_path = $file_path
                    AND cl.repo_url = $repo_url
                    AND cl.start_line <= $start_line
                    AND cl.end_line >= $end_line
                    RETURN cl
                    ORDER BY (cl.end_line - cl.start_line) ASC
                    LIMIT 1
                    """
                    
                    find_params = {
                        "file_path": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "repo_url": repo_url
                    }
                    
                    class_by_range = await db_manager.run_query(find_class_query, find_params)
                    
                    if class_by_range and len(class_by_range) > 0:
                        # Create relationship to the found class
                        rel_query = """
                        MATCH (cl:Class) WHERE id(cl) = $class_id
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MERGE (cl)-[:CONTAINS]->(cc)
                        """
                        
                        rel_params = {
                            "class_id": class_by_range[0]["cl"].id,
                            "chunk_id": chunk_id
                        }
                        
                        await db_manager.run_query(rel_query, rel_params)
                        success = True
                else:
                    # Successfully connected to class
                    success = True
                
            elif parent_type == "Function":
                # Try to find by unique_id first
                function_query = """
                MATCH (fn:Function {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                MERGE (fn)-[:CONTAINS]->(cc)
                RETURN fn
                """
                
                function_params = {
                    "unique_id": parent_id,
                    "chunk_id": chunk_id,
                    "repo_url": repo_url
                }
                
                function_result = await db_manager.run_query(function_query, function_params)
                
                # If no function found by unique_id, try to find by line range
                if not function_result or len(function_result) == 0:
                    # Try to find a function that contains this chunk's line range
                    find_function_query = """
                    MATCH (fn:Function)
                    WHERE fn.file_path = $file_path
                    AND fn.repo_url = $repo_url
                    AND fn.start_line <= $start_line
                    AND fn.end_line >= $end_line
                    RETURN fn
                    ORDER BY (fn.end_line - fn.start_line) ASC
                    LIMIT 1
                    """
                    
                    find_params = {
                        "file_path": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "repo_url": repo_url
                    }
                    
                    function_by_range = await db_manager.run_query(find_function_query, find_params)
                    
                    if function_by_range and len(function_by_range) > 0:
                        # Create relationship to the found function
                        rel_query = """
                        MATCH (fn:Function) WHERE id(fn) = $function_id
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MERGE (fn)-[:CONTAINS]->(cc)
                        """
                        
                        rel_params = {
                            "function_id": function_by_range[0]["fn"].id,
                            "chunk_id": chunk_id
                        }
                        
                        await db_manager.run_query(rel_query, rel_params)
                        success = True
                else:
                    # Successfully connected to function
                    success = True
            
            # If we haven't successfully connected to a Class or Function, connect to File
            if not success or parent_type == "File":
                # First make sure we've normalized the file path
                if is_protobuf:
                    # For protobuf files, try multiple potential path formats
                    # Example: src/cartservice/src/protos/Cart.proto or protos/Cart.proto
                    file_paths_to_try = [
                        file_path,
                        os.path.basename(file_path),
                        file_path.replace('proto/', 'protos/'),
                        file_path.replace('protos/', 'proto/')
                    ]
                else:
                    file_paths_to_try = [file_path]
                
                # Try all potential file paths
                file_connected = False
                for path_to_try in file_paths_to_try:
                    if not path_to_try:
                        continue
                        
                    # Connect to the File
                    file_rel_query = """
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                    MERGE (f)-[:CONTAINS]->(cc)
                    RETURN f
                    """
                    
                    file_params = {
                        "file_path": path_to_try,
                        "chunk_id": chunk_id,
                        "repo_url": repo_url
                    }
                    
                    file_result = await db_manager.run_query(file_rel_query, file_params)
                    
                    if file_result and len(file_result) > 0:
                        # Update the file path if it was different
                        if path_to_try != file_path:
                            update_query = """
                            MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                            SET cc.file_path = $file_path
                            """
                            await db_manager.run_query(update_query, {"chunk_id": chunk_id, "file_path": path_to_try})
                        
                        # Connect to Service
                        service_query = """
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MATCH (s:Service {name: $service_name})
                        MERGE (cc)-[:BELONGS_TO]->(s)
                        """
                        await db_manager.run_query(service_query, {"chunk_id": chunk_id, "service_name": service_name})
                        
                        file_connected = True
                        logger.info(f"Connected {chunk_id} to file {path_to_try}")
                        break
                
                # If exact file paths failed, try fuzzy matching
                if not file_connected:
                    # Try to find any file in this repo that might contain this chunk
                    fuzzy_file_query = """
                    MATCH (f:File)
                    WHERE f.repo_url = $repo_url
                    AND f.path ENDS WITH $filename
                    RETURN f
                    LIMIT 1
                    """
                    
                    filename = os.path.basename(file_path)
                    fuzzy_params = {
                        "repo_url": repo_url,
                        "filename": filename
                    }
                    
                    fuzzy_result = await db_manager.run_query(fuzzy_file_query, fuzzy_params)
                    
                    if fuzzy_result and len(fuzzy_result) > 0:
                        # Create relationship to the found file
                        fuzzy_rel_query = """
                        MATCH (f:File) WHERE id(f) = $file_id
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MERGE (f)-[:CONTAINS]->(cc)
                        
                        WITH cc, f
                        MATCH (s:Service {name: $service_name})
                        MERGE (cc)-[:BELONGS_TO]->(s)
                        """
                        
                        fuzzy_params = {
                            "file_id": fuzzy_result[0]["f"].id,
                            "chunk_id": chunk_id,
                            "service_name": service_name
                        }
                        
                        await db_manager.run_query(fuzzy_rel_query, fuzzy_params)
                        logger.info(f"Created relationship to file via fuzzy match for {chunk_id}")
                        file_connected = True
                
                # Only use repository fallback as a last resort
                if not file_connected:
                    # Create a proper file node first rather than falling back directly to repository
                    await self._ensure_file_node_exists(file_path, repo_url, service_name)
                    
                    # Try one more time with the newly created file node
                    final_file_query = """
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                    MERGE (f)-[:CONTAINS]->(cc)
                    RETURN f
                    """
                    final_params = {
                        "file_path": file_path,
                        "chunk_id": chunk_id,
                        "repo_url": repo_url
                    }
                    
                    final_result = await db_manager.run_query(final_file_query, final_params)
                    
                    if final_result and len(final_result) > 0:
                        logger.info(f"Connected {chunk_id} to newly created file node {file_path}")
                        
                        # Connect to Service
                        service_query = """
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MATCH (s:Service {name: $service_name})
                        MERGE (cc)-[:BELONGS_TO]->(s)
                        """
                        await db_manager.run_query(service_query, {"chunk_id": chunk_id, "service_name": service_name})
                    else:
                        # Final fallback - try to use repository as parent to avoid completely orphaned chunks
                        repo_rel_query = """
                        MATCH (r:Repository {url: $repo_url})
                        MATCH (cc:CodeChunk {chunk_id: $chunk_id})
                        MERGE (r)-[:CONTAINS]->(cc)
                        
                        WITH cc, r
                        MATCH (s:Service {name: $service_name})
                        MERGE (cc)-[:BELONGS_TO]->(s)
                        RETURN cc
                        """
                        
                        repo_params = {
                            "repo_url": repo_url,
                            "chunk_id": chunk_id,
                            "service_name": service_name
                        }
                        
                        await db_manager.run_query(repo_rel_query, repo_params)
                        logger.warning(f"Created fallback relationship to repository for {chunk_id} - this should be avoided")
            
        except Exception as e:
            logger.error(f"Error creating CodeChunk node for {chunk_id}: {e}")
            # Continue processing other chunks

    async def _ensure_file_node_exists(self, file_path: str, repo_url: str, service_name: str):
        """
        Ensure that a File node exists for the given path. Create it if it doesn't.
        
        Args:
            file_path: The file path to check/create
            repo_url: Repository URL
            service_name: Service name
        """
        if not file_path:
            return
            
        # Normalize the file path by removing duplicate repository name
        file_path = self._normalize_path(file_path, repo_url)
            
        # Check if file exists
        check_query = """
        MATCH (f:File {path: $file_path, repo_url: $repo_url})
        RETURN f
        """
        
        check_result = await db_manager.run_query(check_query, {"file_path": file_path, "repo_url": repo_url})
        
        if not check_result or len(check_result) == 0:
            # File doesn't exist, create it
            file_name = os.path.basename(file_path)
            language = self._detect_language(file_path)
            
            await self._create_file_node(
                path=file_path,
                name=file_name,
                language=language,
                file_type=language,
                repo_url=repo_url,
                service_name=service_name
            )
            logger.info(f"Created missing File node for {file_path}")
            
            # Ensure the file is also connected to the repository
            repo_link_query = """
            MATCH (r:Repository {url: $repo_url})
            MATCH (f:File {path: $file_path, repo_url: $repo_url})
            MERGE (f)-[:BELONGS_TO]->(r)
            """
            
            await db_manager.run_query(repo_link_query, {"repo_url": repo_url, "file_path": file_path})

    async def _process_file(self, file_data):
        """
        Process a file and create the appropriate nodes.
        
        Args:
            file_data: Dictionary containing file information
        
        Returns:
            Created File node
        """
        file_path = file_data.get('path')
        if not file_path:
            logger.warning("File data missing path, skipping.")
            return None
            
        # Skip files with parse errors
        if file_data.get('parse_error', False):
            logger.warning(f"Skipping file with parse error: {file_path}")
            return None
            
        # Normalize path
        file_path = self._normalize_path(file_path, self.repo_url)
        file_data['path'] = file_path  # Update the path in the file_data
            
        # Extract file properties
        file_name = os.path.basename(file_path)
        language = file_data.get('language', self._detect_language(file_path))
        
        # Create file properties
        file_props = {
            'name': file_name,
            'path': file_path,
            'language': language,
            'repo_url': self.repo_url,
            'content_hash': self._hash_content(file_data.get('content', '')),
            'is_documentation': file_data.get('is_documentation', False) or file_name.lower() == 'readme.md' or file_path.lower().endswith('.md')
        }
        
        # Extract repository name from the URL for better tracking
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        
        # Determine service name (default to repository name without extension)
        service_name = repo_name.replace('.git', '')
        
        # Create File node in Neo4j
        file_node = await self._create_file_node(
            path=file_path,
            name=file_name,
            language=language,
            file_type=self._detect_language(file_path),
            repo_url=self.repo_url,
            service_name=service_name
        )
        
        # Process special file types
        if language == 'protobuf':
            await self._process_protobuf_file(file_path, file_data)
        
        # Process functions in the file
        for func_data in file_data.get('functions', []):
            await self._process_function_node(func_data, file_path)
            
        # Process classes in the file
        for class_data in file_data.get('classes', []):
            await self._process_class_node(class_data, file_path)
            
        return file_node
        
    async def _process_protobuf_file(self, file_path, file_data):
        """
        Process a protobuf file and create message and service nodes.
        
        Args:
            file_path: The file path for the protobuf file
            file_data: Dictionary containing file information
        """
        # Extract repository name from the URL for better tracking
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        
        # Determine service name (default to repository name without extension)
        service_name = repo_name.replace('.git', '')
        
        # First, ensure the protobuf file is properly recorded
        await self._ensure_file_node_exists(file_path, self.repo_url, service_name)
        
        # Store all proto file locations to handle duplicates
        proto_files = await self._find_all_proto_file_paths(file_path, self.repo_url)
        
        # Process messages (data models)
        for message in file_data.get('messages', []):
            unique_id = message.get('unique_id')
            name = message.get('name')
            start_line = message.get('start_line')
            end_line = message.get('end_line')
            
            # Create DataModel node
            await self._create_class_node(
                unique_id=unique_id,
                name=name,
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
                repo_url=self.repo_url,
                service_name=service_name,
                is_data_model=True
            )
            
            # Connect this class to all duplicate proto files
            for proto_path in proto_files:
                link_query = """
                MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (f:File {path: $file_path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(cl)
                """
                
                await db_manager.run_query(link_query, {
                    "unique_id": unique_id,
                    "file_path": proto_path,
                    "repo_url": self.repo_url
                })
            
            # Log creation
            logger.info(f"Created DataModel node for protobuf message: {name}")
            
        # Process services (APIs)
        for service in file_data.get('services', []):
            unique_id = service.get('unique_id')
            name = service.get('name')
            start_line = service.get('start_line')
            end_line = service.get('end_line')
            
            # Create ApiEndpoint node
            await self._create_class_node(
                unique_id=unique_id,
                name=name,
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
                repo_url=self.repo_url,
                service_name=service_name,
                is_api=True
            )
            
            # Connect this class to all duplicate proto files
            for proto_path in proto_files:
                link_query = """
                MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
                MATCH (f:File {path: $file_path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(cl)
                """
                
                await db_manager.run_query(link_query, {
                    "unique_id": unique_id,
                    "file_path": proto_path,
                    "repo_url": self.repo_url
                })
            
            # Log creation
            logger.info(f"Created ApiEndpoint node for protobuf service: {name}")

    async def _find_all_proto_file_paths(self, file_path: str, repo_url: str):
        """
        Find all versions of a proto file by its basename.
        
        Args:
            file_path: The primary file path
            repo_url: Repository URL
            
        Returns:
            List of all paths for this proto file
        """
        filename = os.path.basename(file_path)
        
        query = """
        MATCH (f:File)
        WHERE f.repo_url = $repo_url
        AND f.path ENDS WITH $filename
        RETURN f.path as path
        """
        
        result = await db_manager.run_query(query, {"repo_url": repo_url, "filename": filename})
        
        # Return all paths found plus the original path
        paths = [r["path"] for r in result]
        if file_path not in paths:
            paths.append(file_path)
            
        return paths

    async def _process_function_node(self, func_data, file_path):
        """
        Process a function and create the appropriate nodes.
        
        Args:
            func_data: Dictionary containing function information
            file_path: The file path that contains this function
        """
        # Extract repository name from the URL for better tracking
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        
        # Determine service name (default to repository name without extension)
        service_name = repo_name.replace('.git', '')
        
        # Extract function properties
        unique_id = func_data.get('unique_id')
        name = func_data.get('name')
        start_line = func_data.get('start_line')
        end_line = func_data.get('end_line')
        
        # Create Function node
        await self._create_function_node(
            unique_id=unique_id,
            name=name,
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
            repo_url=self.repo_url,
            service_name=service_name
        )
        
        # Now create the relationship between the function and its parent file
        link_query = """
        MATCH (fn:Function {unique_id: $unique_id, repo_url: $repo_url})
        MATCH (f:File {path: $file_path, repo_url: $repo_url})
        MERGE (f)-[:CONTAINS]->(fn)
        """
        link_params = {
            "unique_id": unique_id,
            "file_path": file_path,
            "repo_url": self.repo_url
        }
        
        try:
            await db_manager.run_query(link_query, link_params)
            logger.debug(f"Created relationship between file {file_path} and function {name}")
        except Exception as e:
            logger.error(f"Error linking function {name} to file {file_path}: {e}")

    async def _process_class_node(self, class_data, file_path):
        """
        Process a class and create the appropriate nodes.
        
        Args:
            class_data: Dictionary containing class information
            file_path: The file path that contains this class
        """
        # Extract repository name from the URL for better tracking
        repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        
        # Determine service name (default to repository name without extension)
        service_name = repo_name.replace('.git', '')
        
        # Extract class properties
        unique_id = class_data.get('unique_id')
        name = class_data.get('name')
        start_line = class_data.get('start_line')
        end_line = class_data.get('end_line')
        
        # Create Class node
        await self._create_class_node(
            unique_id=unique_id,
            name=name,
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
            repo_url=self.repo_url,
            service_name=service_name
        )
        
        # Now create the relationship between the class and its parent file
        link_query = """
        MATCH (cl:Class {unique_id: $unique_id, repo_url: $repo_url})
        MATCH (f:File {path: $file_path, repo_url: $repo_url})
        MERGE (f)-[:CONTAINS]->(cl)
        """
        link_params = {
            "unique_id": unique_id,
            "file_path": file_path,
            "repo_url": self.repo_url
        }
        
        try:
            await db_manager.run_query(link_query, link_params)
            logger.debug(f"Created relationship between file {file_path} and class {name}")
        except Exception as e:
            logger.error(f"Error linking class {name} to file {file_path}: {e}")

    def _detect_language(self, file_path):
        """Detect language based on file extension"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Map file extensions to languages
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.scala': 'scala',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.m': 'objective-c',
            '.cs': 'csharp',
            '.proto': 'protobuf',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sql': 'sql',
            '.sh': 'shell',
            '.bash': 'shell'
        }
        
        return language_map.get(ext, 'unknown')
        
    def _hash_content(self, content):
        """Create a hash for the content"""
        if not content:
            return ""
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _create_relationship(self, source_node, relationship_type, target_node):
        """
        Create a relationship between two nodes.
        
        Args:
            source_node: Source node
            relationship_type: Type of relationship
            target_node: Target node
            
        Returns:
            Created relationship
        """
        # Ensure both nodes have IDs
        if not source_node.get('id') or not target_node.get('id'):
            logger.warning(f"Cannot create relationship. Missing node IDs: Source: {source_node.get('id')}, Target: {target_node.get('id')}")
            return None
            
        # Log creation of important relationships
        if relationship_type == 'CONTAINS' and source_node.get('name') != target_node.get('name'):
            logger.debug(f"Creating relationship: {source_node.get('name')} {relationship_type} {target_node.get('name')}")
            
        # Create relationship data
        relationship = {
            'source_id': source_node['id'],
            'target_id': target_node['id'],
            'type': relationship_type
        }
        
        return relationship