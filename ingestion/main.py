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
    def __init__(self, repo_path: str, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
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
                    with open(os.path.join(k8s_path, filename)) as f:
                        try:
                            manifest = yaml.safe_load(f)
                            if manifest.get('kind') == 'Deployment':
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

def main():
    """Main entry point for microservices ingestion."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Get configuration from environment or config file
    repo_path = os.getenv("REPO_PATH", "./cloned_repo")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

    ingestion = None
    try:
        # Initialize and run ingestion
        ingestion = MicroservicesIngestion(repo_path, neo4j_uri, neo4j_user, neo4j_password)
        ingestion.process_all_services()
        logger.info("Successfully completed ingestion of all services")

    except Exception as e:
        logger.error(f"Error during ingestion: {e}", exc_info=True)
        if isinstance(e, RuntimeError) and "Failed to clone repository" in str(e):
            logger.error("Please ensure you have git installed and can access GitHub")
        elif isinstance(e, ValueError) and "Source directory not found" in str(e):
            logger.error("Repository structure is not as expected. Please check the repository contents")
    finally:
        # Clean up resources
        if ingestion:
            try:
                ingestion.close()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    main()