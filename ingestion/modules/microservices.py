"""
Module for ingesting microservices-based repositories.
"""
import logging
import os
import subprocess
from typing import Dict, Any

from ingestion.config import ingestion_settings
from ingestion.loading.microservices_loader import MicroservicesLoader
from ingestion.parsing.tree_sitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)

class MicroservicesIngestion:
    """
    Class for analyzing and ingesting microservices architecture.
    """
    
    def __init__(self, repo_path: str, neo4j_uri: str = None, neo4j_user: str = None, 
                 neo4j_password: str = None, repo_url: str = None):
        """
        Initialize the microservices ingestion process.
        
        Args:
            repo_path: Path to repository with microservices
            neo4j_uri: Neo4j database URI (optional)
            neo4j_user: Neo4j username (optional)
            neo4j_password: Neo4j password (optional)
            repo_url: URL of the repository (optional)
        """
        # Get repo URL from parameters or environment variables to avoid hardcoding
        self.repo_url = repo_url or os.getenv("INGEST_REPO_URL") or ingestion_settings.ingest_repo_url
        logger.info(f"Using microservices repository URL: {self.repo_url}")
        
        # If repo_path is provided, use it directly
        if repo_path and repo_path != "./cloned_repo" and not repo_path.endswith("/cloned_repo"):
            self.repo_path = repo_path
            logger.info(f"Using provided repository path: {self.repo_path}")
        else:
            # Use the same directory as ingestion_settings to avoid duplicates
            # Get repo name from ingestion_settings to be consistent
            repo_name = ingestion_settings.extract_repo_name(self.repo_url)
            self.repo_path = os.path.join(ingestion_settings.base_clone_dir, repo_name)
            logger.info(f"Using consistent repository path: {self.repo_path}")
            
        self.loader = MicroservicesLoader(neo4j_uri, neo4j_user, neo4j_password)
        self.parser = TreeSitterParser()
        
        # Service metadata from configuration
        self.service_metadata = {}
        
        # Ensure repository exists
        self.clone_repository()
        self.load_service_metadata()
    
    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """Extract repository name from URL."""
        # Simple approach: use the last part of the URL without the .git extension
        if not repo_url:
            return "unknown_repo"
            
        # Remove trailing slashes and .git extension
        clean_url = repo_url.rstrip('/').rstrip('.git')
        
        # Get the last part of the URL (the repo name)
        parts = clean_url.split('/')
        repo_name = parts[-1]
        
        # Replace any problematic characters with underscores
        repo_name = repo_name.replace('.', '_').replace('-', '_')
        
        return repo_name

    def clone_repository(self):
        """Clone the microservices-demo repository if it doesn't exist."""
        # Check if repository URL is set
        if not self.repo_url:
            logger.error("No repository URL provided and none found in environment variables")
            raise ValueError("Repository URL is required for cloning. Please provide a valid URL.")
            
        logger.info(f"Checking repository path: {self.repo_path}")
        if not os.path.exists(self.repo_path):
            logger.info(f"Creating directory: {self.repo_path}")
            os.makedirs(self.repo_path, exist_ok=True)
        
        # Check if repo is already cloned by looking for .git
        git_dir = os.path.join(self.repo_path, ".git")
        if not os.path.exists(git_dir):
            logger.info(f"Cloning repository to {self.repo_path}...")
            try:
                # Clone the repository
                subprocess.run([
                    "git", "clone", "--depth", "1",
                    self.repo_url,
                    self.repo_path
                ], check=True)
                logger.info("Repository cloned successfully")
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Failed to clone repository: {e}")
        else:
            logger.info("Repository already exists, skipping clone")

    def load_service_metadata(self):
        """Load service metadata from kubernetes manifests or docker-compose."""
        import yaml
        
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
        """
        Detect the primary language of a service.
        
        Args:
            service_path: Path to the service directory
            
        Returns:
            Primary language of the service or None if not detected
        """
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
        """
        Process a single microservice directory.
        
        Args:
            service_path: Path to the service directory
            service_name: Name of the service
        
        Returns:
            Dictionary with service data or None if processing failed
        """
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
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Check if src directory exists
        src_path = os.path.join(self.repo_path, "src")
        if not os.path.exists(src_path):
            logger.warning(f"Source directory not found at: {src_path}")
            # Try to find microservices at the repository root
            logger.info(f"Looking for microservices at repository root: {self.repo_path}")
            src_path = self.repo_path

        # Create indices for better performance
        self.loader.create_indices()

        # Process each directory that looks like a service
        with ThreadPoolExecutor() as executor:
            future_to_service = {}
            for service_dir in os.listdir(src_path):
                service_path = os.path.join(src_path, service_dir)
                if os.path.isdir(service_path):
                    # Check if this looks like a service directory (contains code files)
                    has_code_files = False
                    for root, _, files in os.walk(service_path):
                        if any(file.endswith(('.py', '.go', '.cs', '.java', '.js', '.ts')) for file in files):
                            has_code_files = True
                            break
                    
                    if has_code_files:
                        future = executor.submit(self.process_service, service_path, service_dir)
                        future_to_service[future] = service_dir
                    else:
                        logger.debug(f"Skipping directory without code files: {service_dir}")

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