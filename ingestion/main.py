# ingestion/main.py
import asyncio
import logging
import os
import time
from typing import Dict, Any, List
import yaml
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging early
# You might want a more sophisticated setup using app.core.logging_conf later
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import necessary components AFTER basic logging is configured
from ingestion.config import ingestion_settings, get_target_extensions
from ingestion.sources.git_loader import GitLoader
from ingestion.parsing.tree_sitter_parser import TreeSitterParser
from ingestion.processing.chunking import chunk_code
from ingestion.processing.embedding import embed_chunks
from ingestion.loading.neo4j_loader import Neo4jLoader
from ingestion.loading.microservices_loader import MicroservicesLoader  # Fixed import path
from app.db.neo4j_manager import db_manager # Import the instantiated manager
from app.core.config import settings # For embedding dimensions

async def ingestion_pipeline():
    """Runs the full ingestion pipeline."""
    start_time = time.time()
    logger.info("Starting ingestion pipeline...")

    # 0. Connect to DB and ensure schema
    try:
        await db_manager.connect()
        # Ensure dimensions from settings are used
        await db_manager.ensure_constraints_indexes(settings.embedding_dimensions)
    except Exception as e:
        logger.critical(f"Failed to connect to Neo4j or ensure schema: {e}. Aborting.", exc_info=True)
        return # Stop pipeline if DB connection fails

    repo_url = ingestion_settings.ingest_repo_url
    force_reindex = ingestion_settings.force_reindex

    # 1. Check Repository Status
    try:
        last_indexed_sha = await db_manager.get_repository_status(repo_url)
        logger.info(f"Last indexed commit SHA for {repo_url}: {last_indexed_sha}")
    except Exception as e:
        logger.error(f"Failed to get repository status from Neo4j: {e}. Assuming re-index needed.", exc_info=True)
        last_indexed_sha = None # Proceed as if not indexed

    # 2. Load Repository and Check for Changes
    try:
        loader = GitLoader(
            repo_url=repo_url,
            clone_dir=ingestion_settings.clone_dir,
            branch=ingestion_settings.ingest_repo_branch
        )
        repo, current_commit_sha = loader.get_repo_and_commit()
        logger.info(f"Current commit SHA for {repo_url}: {current_commit_sha}")

        if not force_reindex and last_indexed_sha == current_commit_sha:
            logger.info("Repository commit SHA matches last indexed SHA. No changes detected. Skipping ingestion.")
            await db_manager.close()
            return # Exit early

        if force_reindex:
             logger.warning(f"Force re-indexing requested for {repo_url}.")
        elif last_indexed_sha:
             logger.info(f"Commit SHA changed (Current: {current_commit_sha}, Indexed: {last_indexed_sha}). Re-indexing repository.")
        else:
             logger.info(f"Repository not previously indexed or status unknown. Indexing {repo_url}.")

        # Clear old data before re-indexing
        # Caution: Consider alternative strategies (versioning, soft delete) in production
        logger.warning(f"Clearing existing data for {repo_url} before re-indexing...")
        await db_manager.clear_repository_data(repo_url)
        logger.info("Existing data cleared.")


        # 3. Get File Contents
        target_extensions = get_target_extensions()
        files_content = loader.get_files_content(target_extensions) # List of (path, content) tuples

        if not files_content:
            logger.warning("No files found matching target extensions. Ingestion finished.")
            await db_manager.update_repository_status(repo_url, current_commit_sha) # Mark as processed
            await db_manager.close()
            return

    except Exception as e:
        logger.critical(f"Failed during repository loading or file retrieval: {e}. Aborting.", exc_info=True)
        await db_manager.close()
        return


    # 4. Parse Files
    # Assuming only one language initially based on extensions
    # More complex logic needed for multi-language repos
    parsed_data = []
    logger.info(f"Parsing {len(files_content)} files...")

    # --- Improved Language Detection ---
    extension_to_language = {
        ".py": "python",
        ".go": "go",
        ".cs": "csharp", # Use the key expected by our parser init
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript", # Example: Treat jsx as js
        ".ts": "typescript", # Add if you install typescript grammar
        ".tsx": "typescript",
        # Add other mappings as needed
    }

    for file_path, content in files_content:
        _, ext = os.path.splitext(file_path)
        language = extension_to_language.get(ext.lower())

        if not language:
            logger.debug(f"Skipping structural parsing for file with unmapped extension: {file_path}")
            # Optionally create a basic File node entry even if not parsed
            # parsed_data.append({"path": file_path, "language": "unknown", "parse_error": True})
            continue # Skip parsing if language unknown/unsupported

        try:
            # Pass detected language
            result = TreeSitterParser.parse_file(file_path, content, language)
            if result:
                result['language'] = language # Store detected language
                parsed_data.append(result)
            else:
                 # parse_file returned None, meaning unsupported language or major parse fail handled internally
                 logger.debug(f"No structural data extracted for {file_path} (Language: {language})")
                 # Still create a basic File node entry
                 parsed_data.append({"path": file_path, "language": language, "parse_error": True})

        except Exception as e:
            logger.error(f"Critical error parsing file {file_path} ({language}): {e}", exc_info=True)
            # Add placeholder to know it was attempted but failed critically
            parsed_data.append({"path": file_path, "language": language, "parse_error": True})

    logger.info(f"Successfully parsed (or attempted) {len(parsed_data)} files.")


    # 5. Chunk Code
    logger.info("Chunking parsed code content...")
    try:
        # Pass language for appropriate splitter selection
        all_chunks = chunk_code(parsed_data, language)
    except Exception as e:
        logger.critical(f"Failed during chunking: {e}. Aborting.", exc_info=True)
        await db_manager.close()
        return


    # 6. Generate Embeddings
    logger.info("Generating embeddings for chunks...")
    try:
        chunks_with_embeddings = await embed_chunks(all_chunks)
        if not chunks_with_embeddings:
             logger.warning("No chunks were successfully embedded. Check OpenAI API key and service status.")
             # Still update repo status to avoid retrying immediately if there are persistent issues
             await db_manager.update_repository_status(repo_url, current_commit_sha)
             await db_manager.close()
             return

    except Exception as e:
        logger.critical(f"Failed during embedding generation: {e}. Aborting.", exc_info=True)
        await db_manager.close()
        return


    # 7. Load into Neo4j
    logger.info("Loading processed data into Neo4j...")
    try:
        neo4j_loader = Neo4jLoader(repo_url=repo_url)
        await neo4j_loader.load_data(parsed_data, chunks_with_embeddings)
    except Exception as e:
        logger.critical(f"Failed during Neo4j loading: {e}. Aborting.", exc_info=True)
        # Ingestion failed, DO NOT update the commit SHA status
        await db_manager.close()
        return


    # 8. Update Repository Status on Success
    try:
        await db_manager.update_repository_status(repo_url, current_commit_sha)
        logger.info(f"Successfully updated repository status for {repo_url} to commit {current_commit_sha}")
    except Exception as e:
         logger.error(f"Failed to update repository status in Neo4j after successful load: {e}", exc_info=True)
         # Loading succeeded, but status update failed. Log prominently.


    # 9. Cleanup
    await db_manager.close()
    end_time = time.time()
    logger.info(f"Ingestion pipeline finished successfully in {end_time - start_time:.2f} seconds.")


def run_ingestion():
    """Synchronous entry point for running the async pipeline."""
    try:
        asyncio.run(ingestion_pipeline())
    except Exception as e:
        logger.critical(f"Unhandled exception in ingestion pipeline: {e}", exc_info=True)

class MicroservicesIngestion:
    def __init__(self, repo_path: str, neo4j_uri: str = None, neo4j_user: str = None, neo4j_password: str = None):
        self.repo_path = repo_path
        self.loader = MicroservicesLoader(neo4j_uri, neo4j_user, neo4j_password)
        self.parser = TreeSitterParser()
        
        # Service metadata from configuration
        self.service_metadata = {}
        
        # Ensure repository exists
        self.clone_repository()
        self.load_service_metadata()

    def clone_repository(self):
        """Clone the microservices-demo repository if it doesn't exist."""
        if not os.path.exists(self.repo_path):
            logger.info(f"Creating directory: {self.repo_path}")
            os.makedirs(self.repo_path)
        
        src_path = os.path.join(self.repo_path, "src")
        if not os.path.exists(src_path):
            logger.info("Cloning microservices-demo repository...")
            import subprocess
            try:
                # Clone the repository
                subprocess.run([
                    "git", "clone", "--depth", "1",
                    "https://github.com/GoogleCloudPlatform/microservices-demo.git",
                    self.repo_path
                ], check=True)
                logger.info("Repository cloned successfully")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone repository: {e}")
        else:
            logger.info("Repository already exists, skipping clone")

    def load_service_metadata(self):
        """Load service metadata from kubernetes manifests or docker-compose."""
        k8s_path = os.path.join(self.repo_path, "kubernetes-manifests")
        compose_path = os.path.join(self.repo_path, "docker-compose.yaml")
        
        if os.path.exists(k8s_path):
            for filename in os.listdir(k8s_path):
                if filename.endswith(('.yaml', '.yml')):
                    try:
                        with open(os.path.join(k8s_path, filename)) as f:
                            # Parse all documents in the YAML file
                            documents = list(yaml.safe_load_all(f))
                            for manifest in documents:
                                if manifest and manifest.get('kind') == 'Deployment':
                                    service_name = manifest['metadata']['name']
                                    self.service_metadata[service_name] = {
                                        'containers': manifest['spec']['template']['spec']['containers'],
                                        'labels': manifest['metadata'].get('labels', {}),
                                        'annotations': manifest['metadata'].get('annotations', {})
                                    }
                    except yaml.YAMLError as e:
                        logger.error(f"Error parsing {filename}: {e}")
        elif os.path.exists(compose_path):
            try:
                with open(compose_path) as f:
                    compose = yaml.safe_load(f)
                    for service_name, service_def in compose.get('services', {}).items():
                        self.service_metadata[service_name] = service_def
            except yaml.YAMLError as e:
                logger.error(f"Error parsing docker-compose.yaml: {e}")

    def detect_language(self, service_path: str) -> str:
        """Detect the primary language of a service."""
        extension_map = {
            '.py': 'python',
            '.go': 'go',
            '.cs': 'csharp',
            '.java': 'java',
            '.js': 'javascript',
            '.ts': 'typescript'
        }
        
        extensions = {}
        for root, _, files in os.walk(service_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in extension_map:
                    extensions[ext] = extensions.get(ext, 0) + 1
        
        if not extensions:
            return None
            
        primary_ext = max(extensions.items(), key=lambda x: x[1])[0]
        return extension_map[primary_ext]

    def process_service(self, service_path: str, service_name: str) -> Dict[str, Any]:
        """Process a single microservice directory."""
        language = self.detect_language(service_path)
        if not language:
            logger.warning(f"Could not detect language for service: {service_name}")
            return None

        service_data = {
            "service_name": service_name,
            "language": language,
            "files": [],
            "relationships": {
                "service_calls": [],
                "data_dependencies": [],
                "event_flows": [],
                "config_dependencies": []
            }
        }

        # Add metadata from k8s/docker-compose
        if service_name in self.service_metadata:
            service_data.update({
                "metadata": self.service_metadata[service_name]
            })

        # Process each file in the service
        for root, _, files in os.walk(service_path):
            for file in files:
                if file.endswith(('.py', '.go', '.cs', '.java', '.js', '.ts')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            parsed = self.parser.parse_file(file_path, content, language)
                            if parsed:
                                service_data["files"].append(parsed)
                                
                                # Merge relationships
                                for rel_type, rels in parsed.get("relationships", {}).items():
                                    if rels:
                                        service_data["relationships"][rel_type].extend(rels)
                                
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {e}")

        return service_data

    def process_all_services(self):
        """Process all microservices in the repository."""
        src_path = os.path.join(self.repo_path, "src")
        if not os.path.exists(src_path):
            raise ValueError(f"Source directory not found: {src_path}")

        # Create indices for better performance
        self.loader.create_indices()

        # Process each service directory in parallel
        with ThreadPoolExecutor() as executor:
            future_to_service = {}
            for service_dir in os.listdir(src_path):
                service_path = os.path.join(src_path, service_dir)
                if os.path.isdir(service_path):
                    future = executor.submit(self.process_service, service_path, service_dir)
                    future_to_service[future] = service_dir

            for future in as_completed(future_to_service):
                service_name = future_to_service[future]
                try:
                    service_data = future.result()
                    if service_data:
                        self.loader.load_microservice_structure(service_data)
                        logger.info(f"Successfully processed service: {service_name}")
                except Exception as e:
                    logger.error(f"Error processing service {service_name}: {e}")

    def close(self):
        """Clean up resources."""
        self.loader.close()

# Comprehensive Knowledge System Ingestion Framework
class EnterpriseKnowledgeSystem:
    """
    Unified knowledge system that integrates code, architecture, documentation,
    and team knowledge into a comprehensive understanding of the software landscape.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the knowledge system with configuration.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = self._load_config(config_path)
        self.db_manager = db_manager  # Use the existing manager
        self.knowledge_sources = []
        self.logger = logger
        
    def _load_config(self, config_path=None):
        """Load configuration from file or use defaults."""
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
        
        # Default configuration
        return {
            "repositories": [
                {
                    "url": ingestion_settings.ingest_repo_url,
                    "branch": ingestion_settings.ingest_repo_branch,
                    "type": "standard"
                }
            ],
            "documentation_sources": [],
            "team_knowledge": {},
            "microservices_analysis": True,  # Always analyze microservices
            "cross_repo_analysis": True      # Always analyze cross-repo relationships
        }
    
    async def connect_database(self):
        """Ensure database connection and schema."""
        try:
            await self.db_manager.connect()
            await self.db_manager.ensure_constraints_indexes(settings.embedding_dimensions)
            
            # Create additional indexes and constraints for cross-repository relationships
            await self._create_cross_repo_schema()
            return True
        except Exception as e:
            logger.critical(f"Failed to connect to database: {e}", exc_info=True)
            return False
    
    async def _create_cross_repo_schema(self):
        """Create schema for cross-repository relationships."""
        try:
            # Create indexes for API endpoints, data models, and service dependencies
            queries = [
                "CREATE INDEX IF NOT EXISTS FOR (a:ApiEndpoint) ON (a.path)",
                "CREATE INDEX IF NOT EXISTS FOR (d:DataModel) ON (d.name)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Service) ON (s.name)",
                "CREATE INDEX IF NOT EXISTS FOR (r:Repository) ON (r.url)",
                "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)"
            ]
            
            for query in queries:
                await self.db_manager.execute_query(query)
                
            logger.info("Cross-repository schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create cross-repository schema: {e}")
            # Continue even if this fails
    
    async def ingest_code_repository(self, repo_config):
        """
        Ingest a standard code repository.
        
        Args:
            repo_config: Repository configuration dictionary
        """
        repo_url = repo_config.get("url")
        branch = repo_config.get("branch")
        service_name = repo_config.get("service_name", self._extract_service_name(repo_url))
        
        # Use existing GitLoader with configuration
        loader = GitLoader(
            repo_url=repo_url,
            clone_dir=ingestion_settings.clone_dir,
            branch=branch
        )
        
        # Check if repository needs reindexing
        last_indexed_sha = await self.db_manager.get_repository_status(repo_url)
        repo, current_commit_sha = loader.get_repo_and_commit()
        
        force_reindex = repo_config.get("force_reindex", False)
        if not force_reindex and last_indexed_sha == current_commit_sha:
            logger.info(f"Repository {repo_url} already indexed at {current_commit_sha}. Skipping.")
            return
        
        # Clear existing data for this repository
        logger.info(f"Clearing existing data for {repo_url} before re-indexing...")
        await self.db_manager.clear_repository_data(repo_url)
        
        # Create Repository node
        await self._create_repository_node(repo_url, service_name, repo_config.get("description", ""))
        
        # Get and process files
        target_extensions = get_target_extensions()
        files_content = loader.get_files_content(target_extensions)
        
        if not files_content:
            logger.warning(f"No files found in {repo_url} matching target extensions.")
            await self.db_manager.update_repository_status(repo_url, current_commit_sha)
            return
        
        # Parse files based on language
        parsed_data = self._parse_files(files_content)
        
        # Extract API definitions and data models
        api_definitions, data_models = self._extract_api_and_data_models(parsed_data, repo_url)
        
        # Process chunks and embeddings
        all_chunks = chunk_code(parsed_data, "auto")
        chunks_with_embeddings = await embed_chunks(all_chunks)
        
        # Load into knowledge graph
        neo4j_loader = Neo4jLoader(repo_url=repo_url)
        await neo4j_loader.load_data(parsed_data, chunks_with_embeddings)
        
        # Load API definitions and data models
        if api_definitions or data_models:
            await self._load_api_and_data_models(api_definitions, data_models, repo_url, service_name)
        
        # Update repository status
        await self.db_manager.update_repository_status(repo_url, current_commit_sha)
        logger.info(f"Successfully indexed repository {repo_url} at commit {current_commit_sha}")
    
    def _extract_service_name(self, repo_url):
        """Extract service name from repository URL."""
        # Example: https://github.com/org/payment-service.git -> payment-service
        try:
            parts = repo_url.rstrip('/').rstrip('.git').split('/')
            return parts[-1]
        except:
            return "unknown-service"
    
    async def _create_repository_node(self, repo_url, service_name, description):
        """Create a Repository node in the graph."""
        query = """
        MERGE (r:Repository {url: $url})
        SET r.service_name = $service_name,
            r.description = $description,
            r.last_updated = datetime()
        RETURN r
        """
        params = {
            "url": repo_url,
            "service_name": service_name,
            "description": description
        }
        
        try:
            await self.db_manager.execute_query(query, params)
            logger.info(f"Created/updated Repository node for {repo_url}")
        except Exception as e:
            logger.error(f"Failed to create Repository node: {e}")
    
    def _extract_api_and_data_models(self, parsed_data, repo_url):
        """
        Extract API definitions and data models from parsed code.
        This is a simplified version - in practice, you'd use more sophisticated
        analysis to detect API endpoints, request/response models, etc.
        """
        api_definitions = []
        data_models = []
        
        # Look for common API patterns in the code
        for file_data in parsed_data:
            if not isinstance(file_data, dict) or file_data.get("parse_error"):
                continue
                
            file_path = file_data.get("path", "")
            language = file_data.get("language", "")
            
            # Check for API definition files
            if any(pattern in file_path.lower() for pattern in [
                "controller", "route", "api", "endpoint", "service", "handler"
            ]):
                # Extract function definitions that might be API endpoints
                functions = file_data.get("functions", [])
                for func in functions:
                    # Simple heuristic for API endpoints
                    if any(method in func.get("name", "").lower() for method in [
                        "get", "post", "put", "delete", "patch"
                    ]):
                        api_definitions.append({
                            "name": func.get("name", ""),
                            "file_path": file_path,
                            "repo_url": repo_url,
                            "language": language,
                            "parameters": func.get("parameters", []),
                            "return_type": func.get("return_type", "unknown"),
                            "docstring": func.get("docstring", "")
                        })
            
            # Check for data model definitions
            if any(pattern in file_path.lower() for pattern in [
                "model", "schema", "dto", "entity", "domain"
            ]):
                # Extract class definitions that might be data models
                classes = file_data.get("classes", [])
                for cls in classes:
                    data_models.append({
                        "name": cls.get("name", ""),
                        "file_path": file_path,
                        "repo_url": repo_url,
                        "language": language,
                        "properties": cls.get("properties", []),
                        "methods": cls.get("methods", []),
                        "docstring": cls.get("docstring", "")
                    })
        
        return api_definitions, data_models
    
    async def _load_api_and_data_models(self, api_definitions, data_models, repo_url, service_name):
        """Load API definitions and data models into the graph database."""
        # Load API endpoints
        for api in api_definitions:
            query = """
            MATCH (r:Repository {url: $repo_url})
            MERGE (a:ApiEndpoint {
                name: $name,
                file_path: $file_path,
                repo_url: $repo_url
            })
            SET a.language = $language,
                a.parameters = $parameters,
                a.return_type = $return_type,
                a.docstring = $docstring,
                a.service_name = $service_name
            MERGE (a)-[:BELONGS_TO]->(r)
            """
            params = {
                "name": api["name"],
                "file_path": api["file_path"],
                "repo_url": repo_url,
                "language": api["language"],
                "parameters": json.dumps(api["parameters"]),
                "return_type": api["return_type"],
                "docstring": api["docstring"],
                "service_name": service_name
            }
            
            try:
                await self.db_manager.execute_query(query, params)
            except Exception as e:
                logger.error(f"Failed to create ApiEndpoint node: {e}")
        
        # Load data models
        for model in data_models:
            query = """
            MATCH (r:Repository {url: $repo_url})
            MERGE (d:DataModel {
                name: $name,
                file_path: $file_path,
                repo_url: $repo_url
            })
            SET d.language = $language,
                d.properties = $properties,
                d.methods = $methods,
                d.docstring = $docstring,
                d.service_name = $service_name
            MERGE (d)-[:BELONGS_TO]->(r)
            """
            params = {
                "name": model["name"],
                "file_path": model["file_path"],
                "repo_url": repo_url,
                "language": model["language"],
                "properties": json.dumps(model["properties"]),
                "methods": json.dumps(model["methods"]),
                "docstring": model["docstring"],
                "service_name": service_name
            }
            
            try:
                await self.db_manager.execute_query(query, params)
            except Exception as e:
                logger.error(f"Failed to create DataModel node: {e}")
    
    async def ingest_microservices(self, repo_path=None):
        """
        Analyze microservices architecture and relationships.
        
        Args:
            repo_path: Path to repository with microservices
        """
        repo_path = repo_path or os.getenv("REPO_PATH", "./cloned_repo")
        
        try:
            ingestion = MicroservicesIngestion(repo_path)
            ingestion.process_all_services()
            logger.info(f"Successfully analyzed microservices architecture from {repo_path}")
            
            # After processing microservices, analyze cross-service relationships
            await self._analyze_cross_service_relationships()
        except Exception as e:
            logger.error(f"Error during microservices analysis: {e}", exc_info=True)
        finally:
            if 'ingestion' in locals():
                ingestion.close()
    
    async def _analyze_cross_service_relationships(self):
        """
        Analyze relationships between services across repositories.
        This identifies API dependencies, shared data models, etc.
        """
        logger.info("Analyzing cross-service relationships...")
        
        try:
            # Find API dependencies between services
            query = """
            // Match API endpoints and potential callers
            MATCH (api:ApiEndpoint)
            MATCH (func:Function)
            WHERE func.repo_url <> api.repo_url
            AND (
                // Look for HTTP client calls that might reference this endpoint
                func.code CONTAINS 'http' OR 
                func.code CONTAINS 'fetch' OR 
                func.code CONTAINS 'axios' OR
                func.code CONTAINS 'request'
            )
            // Create potential dependency relationships
            // In a real implementation, you'd use more sophisticated analysis
            WITH api, func
            WHERE func.code CONTAINS api.name OR func.code CONTAINS REPLACE(api.name, '_', '-')
            MERGE (func)-[:MAY_CALL]->(api)
            RETURN count(*) as relationships
            """
            
            result = await self.db_manager.execute_query(query)
            count = result[0]['relationships'] if result else 0
            logger.info(f"Identified {count} potential cross-service API dependencies")
            
            # Find shared data models between services
            query = """
            // Match data models with similar names across repositories
            MATCH (dm1:DataModel)
            MATCH (dm2:DataModel)
            WHERE dm1.repo_url <> dm2.repo_url
            AND dm1.name = dm2.name
            MERGE (dm1)-[:SIMILAR_TO]->(dm2)
            RETURN count(*) as relationships
            """
            
            result = await self.db_manager.execute_query(query)
            count = result[0]['relationships'] if result else 0
            logger.info(f"Identified {count} potential shared data models across services")
            
        except Exception as e:
            logger.error(f"Error during cross-service relationship analysis: {e}")
    
    def _parse_files(self, files_content):
        """Parse files based on their language."""
        extension_to_language = {
            ".py": "python",
            ".go": "go",
            ".cs": "csharp",
            ".java": "java",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        
        parsed_data = []
        for file_path, content in files_content:
            _, ext = os.path.splitext(file_path)
            language = extension_to_language.get(ext.lower())
            
            if not language:
                logger.debug(f"Skipping parsing for unsupported file: {file_path}")
                continue
                
            try:
                result = TreeSitterParser.parse_file(file_path, content, language)
                if result:
                    result['language'] = language
                    parsed_data.append(result)
                else:
                    parsed_data.append({"path": file_path, "language": language, "parse_error": True})
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")
                parsed_data.append({"path": file_path, "language": language, "parse_error": True})
        
        return parsed_data
    
    async def ingest_documentation(self, doc_sources):
        """
        Ingest documentation from various sources.
        
        Args:
            doc_sources: List of documentation source configurations
        """
        logger.info("Documentation ingestion not yet implemented")
        # TODO: Implement documentation ingestion from Confluence, wikis, etc.
        pass
    
    async def ingest_team_knowledge(self, team_config):
        """
        Ingest team structure and expertise information.
        
        Args:
            team_config: Team knowledge configuration
        """
        logger.info("Team knowledge ingestion not yet implemented")
        # TODO: Implement team knowledge ingestion
        pass
    
    async def run_comprehensive_ingestion(self):
        """Run the comprehensive ingestion pipeline for all configured sources."""
        start_time = time.time()
        logger.info("Starting comprehensive knowledge system ingestion...")
        
        # Connect to database
        if not await self.connect_database():
            return
        
        # Always process both code repositories and microservices architecture
        # to ensure complete relationships in the knowledge graph
        logger.info("Processing all knowledge sources for unified understanding...")
        
        # Process code repositories
        for repo_config in self.config.get("repositories", []):
            await self.ingest_code_repository(repo_config)
        
        # Always process microservices architecture
        repo_path = self.config.get("microservices_repo_path") or os.getenv("REPO_PATH", "./cloned_repo")
        await self.ingest_microservices(repo_path)
        
        # Process documentation sources
        await self.ingest_documentation(self.config.get("documentation_sources", []))
        
        # Process team knowledge
        await self.ingest_team_knowledge(self.config.get("team_knowledge", {}))
        
        # Analyze cross-repository relationships if enabled
        if self.config.get("cross_repo_analysis", True):
            logger.info("Analyzing cross-repository relationships...")
            await self._analyze_cross_repo_relationships()
        
        # Close database connection
        await self.db_manager.close()
        
        end_time = time.time()
        logger.info(f"Comprehensive knowledge system ingestion completed in {end_time - start_time:.2f} seconds")
    
    async def _analyze_cross_repo_relationships(self):
        """
        Analyze relationships between different repositories.
        This identifies dependencies, shared concepts, etc.
        """
        try:
            # Example: Find API contracts that are used across repositories
            query = """
            // Find data models that are used in API endpoints across repositories
            MATCH (dm:DataModel)
            MATCH (api:ApiEndpoint)
            WHERE dm.repo_url <> api.repo_url
            AND (
                api.parameters CONTAINS dm.name OR
                api.return_type CONTAINS dm.name
            )
            MERGE (api)-[:USES_MODEL]->(dm)
            RETURN count(*) as relationships
            """
            
            result = await self.db_manager.execute_query(query)
            count = result[0]['relationships'] if result else 0
            logger.info(f"Identified {count} cross-repository API contract dependencies")
            
        except Exception as e:
            logger.error(f"Error during cross-repository relationship analysis: {e}")

async def comprehensive_ingestion_pipeline(config_path=None):
    """
    Run the comprehensive ingestion pipeline with the unified knowledge system.
    
    Args:
        config_path: Path to configuration file
    """
    knowledge_system = EnterpriseKnowledgeSystem(config_path)
    await knowledge_system.run_comprehensive_ingestion()

def run_comprehensive_ingestion(config_path=None):
    """
    Synchronous entry point for the comprehensive ingestion pipeline.
    
    Args:
        config_path: Path to configuration file
    """
    try:
        asyncio.run(comprehensive_ingestion_pipeline(config_path))
    except Exception as e:
        logger.critical(f"Unhandled exception in comprehensive ingestion: {e}", exc_info=True)

def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enterprise AI Software Knowledge System Ingestion"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--repo-path", 
        type=str, 
        help="Repository path for microservices analysis"
    )
    parser.add_argument(
        "--repos", 
        type=str, 
        nargs='+',
        help="List of repository URLs to ingest (space-separated)"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a config dictionary if repo_path or repos are provided
    config = None
    if args.repo_path or args.repos:
        config = {}
        
        if args.repo_path:
            config["microservices_repo_path"] = args.repo_path
            
        if args.repos:
            config["repositories"] = []
            for repo_url in args.repos:
                config["repositories"].append({
                    "url": repo_url,
                    "service_name": repo_url.split('/')[-1].replace('.git', '')
                })
    
    # Always run comprehensive ingestion
    logger.info("Running unified knowledge system ingestion")
    if config:
        # Create a temporary config file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config, f)
            temp_config_path = f.name
        run_comprehensive_ingestion(temp_config_path)
        # Clean up temp file
        try:
            os.unlink(temp_config_path)
        except:
            pass
    else:
        run_comprehensive_ingestion(args.config)

if __name__ == "__main__":
    main()