"""
Enhanced Knowledge System Module

This module integrates the knowledge_graph builder pattern with the ingestion system
to provide a comprehensive knowledge graph of software systems.
"""

import asyncio
import logging
import os
import json
import tempfile
from typing import Dict, Any, List, Optional, Set, Tuple

from app.db.neo4j_manager import db_manager
from app.core.config import settings
from ingestion.config import ingestion_settings
from ingestion.sources.git_loader import GitLoader
from ingestion.parsing.enhanced_parser import EnhancedParser
from ingestion.processing.chunking import chunk_code, chunk_code_file
from ingestion.processing.embedding import embed_chunks
from ingestion.loading.enhanced_loader import EnhancedLoader
from ingestion.schema import RELATIONSHIP_TYPES, get_node_types, get_relationship_types

logger = logging.getLogger(__name__)


class EnhancedKnowledgeSystem:
    """
    Enhanced knowledge system that integrates the knowledge_graph builder pattern
    with the ingestion system's efficient processing pipeline.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize the enhanced knowledge system.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = self._load_config(config_path)
        self.db_manager = db_manager
        self.created_entities = {}  # Track created entities to avoid duplicates
        
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
            "microservices_analysis": True,
            "cross_repo_analysis": True
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
            # Create indexes for enhanced entity types
            queries = [
                # Core entity indexes
                "CREATE INDEX IF NOT EXISTS FOR (r:Repository) ON (r.url)",
                "CREATE INDEX IF NOT EXISTS FOR (s:Service) ON (s.name)",
                "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.path)",
                "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
                "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)",
                "CREATE INDEX IF NOT EXISTS FOR (cc:CodeChunk) ON (cc.chunk_id)",
                
                # Enhanced entity indexes
                "CREATE INDEX IF NOT EXISTS FOR (api:ApiEndpoint) ON (api.path)",
                "CREATE INDEX IF NOT EXISTS FOR (dm:DataModel) ON (dm.name)",
                "CREATE INDEX IF NOT EXISTS FOR (d:Dependency) ON (d.name)",
                
                # Unique constraints
                "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.url IS UNIQUE",
                # Use a simple uniqueness constraint instead of NODE KEY
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Service) REQUIRE s.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE fn.unique_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE c.unique_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (cc:CodeChunk) REQUIRE cc.chunk_id IS UNIQUE"
            ]
            
            for query in queries:
                await self.db_manager.run_query(query)
                
            logger.info("Enhanced schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create enhanced schema: {e}")
            # Continue even if this fails
    
    async def ingest_repository(self, repo_config):
        """
        Ingest a repository using the enhanced knowledge system.
        
        Args:
            repo_config: Repository configuration dictionary
        """
        repo_url = repo_config.get("url")
        branch = repo_config.get("branch")
        service_name = repo_config.get("service_name", self._extract_service_name(repo_url))
        
        # Use GitLoader with the default spring_petclinic directory
        loader = GitLoader(
            repo_url=repo_url,
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
        
        # Get and process files
        target_extensions = ingestion_settings.ingest_target_extensions.split(',')
        files_content = loader.get_files_content(target_extensions)
        
        if not files_content:
            logger.warning(f"No files found in {repo_url} matching target extensions.")
            await self.db_manager.update_repository_status(repo_url, current_commit_sha)
            return
        
        # Parse files using the enhanced parser
        parsed_data = []
        for file_path, content in files_content:
            # Determine language from file extension
            _, ext = os.path.splitext(file_path)
            language = self._get_language_from_extension(ext.lower())
            
            if not language:
                logger.debug(f"Skipping parsing for file with unsupported extension: {file_path}")
                continue
            
            try:
                # Use the enhanced parser
                result = EnhancedParser.parse_file(file_path, content, language)
                if result:
                    parsed_data.append(result)
                else:
                    # Add basic file entry if parsing returned None
                    parsed_data.append({"path": file_path, "language": language, "parse_error": True})
            except Exception as e:
                logger.error(f"Error parsing file {file_path} ({language}): {e}", exc_info=True)
                parsed_data.append({"path": file_path, "language": language, "parse_error": True})
        
        # Process code chunks and create embeddings
        chunks_with_embeddings = await self._process_code_chunks(files_content)
        
        # Use the enhanced loader to load data into Neo4j
        enhanced_loader = EnhancedLoader(repo_url)
        await enhanced_loader.load_data(parsed_data, chunks_with_embeddings)
        
        # Extract and load API endpoints and data models
        await self._process_api_endpoints(parsed_data, repo_url, service_name)
        await self._process_data_models(parsed_data, repo_url, service_name)
        
        # Update repository status
        await self.db_manager.update_repository_status(repo_url, current_commit_sha)
        
        # Analyze cross-service relationships
        if self.config.get("cross_repo_analysis", True):
            await self._analyze_cross_service_relationships()
        
        logger.info(f"Repository {repo_url} ingestion completed successfully.")
    
    def _extract_service_name(self, repo_url):
        """Extract service name from repository URL."""
        if not repo_url:
            return "unknown-service"
            
        # Remove trailing slashes and .git extension
        clean_url = repo_url.rstrip('/').rstrip('.git')
        
        # Get the last part of the URL (the repo name)
        parts = clean_url.split('/')
        return parts[-1]
    
    def _get_language_from_extension(self, ext: str) -> Optional[str]:
        """Get programming language from file extension."""
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json"
        }
        
        return language_map.get(ext)
    
    async def _process_code_chunks(self, files_content: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Process code files into chunks and generate embeddings.
        
        Args:
            files_content: List of tuples containing (file_path, content)
            
        Returns:
            List of code chunks with embeddings
        """
        logger.info(f"Processing {len(files_content)} files for chunking and embedding")
        
        # Create chunks from files
        chunks = []
        for file_path, content in files_content:
            # Get the file extension and determine language
            _, ext = os.path.splitext(file_path)
            language = self._get_language_from_extension(ext.lower())
            language = language or "unknown"
            
            # Use the new function to create chunks from file content with proper language information
            file_chunks = chunk_code_file(file_path, content, parent_type="File", language=language)
            chunks.extend(file_chunks)
        
        # Embed the chunks
        chunks_with_embeddings = await embed_chunks(chunks)
        
        return chunks_with_embeddings
    
    async def _process_api_endpoints(self, parsed_data, repo_url, service_name):
        """
        Extract and load API endpoints from parsed data.
        
        Args:
            parsed_data: List of parsed file data
            repo_url: Repository URL
            service_name: Service name
        """
        logger.info(f"Loading {len(parsed_data)} API endpoints for {service_name}")
        
        for file_data in parsed_data:
            if file_data.get('parse_error'):
                continue
                
            file_path = file_data.get('path', '')
            api_endpoints = file_data.get('api_endpoints', [])
            
            for endpoint in api_endpoints:
                try:
                    # Create API endpoint node with name property (required by constraint)
                    # Use path as the name to ensure uniqueness
                    query = """
                    MERGE (api:ApiEndpoint {name: $path, repo_url: $repo_url})
                    SET api.path = $path,
                        api.method = $method,
                        api.function = $function,
                        api.framework = $framework,
                        api.file_path = $file_path,
                        api.service_name = $service_name
                    WITH api
                    MATCH (s:Service {name: $service_name})
                    MERGE (s)-[:EXPOSES]->(api)
                    WITH api, $file_path as file_path
                    MATCH (f:File {path: $file_path, repo_url: $repo_url})
                    MERGE (f)-[:CONTAINS]->(api)
                    """
                    
                    params = {
                        "path": endpoint.get('path', '/'),
                        "method": endpoint.get('method', 'GET'),
                        "function": endpoint.get('function', ''),
                        "framework": endpoint.get('framework', ''),
                        "file_path": file_path,
                        "service_name": service_name,
                        "repo_url": repo_url
                    }
                    
                    await self.db_manager.run_query(query, params)
                except Exception as e:
                    logger.error(f"Error creating API endpoint: {e}")
    
    async def _process_data_models(self, parsed_data: List[Dict[str, Any]], repo_url: str, service_name: str):
        """
        Process and load data models into the knowledge graph.
        
        Args:
            parsed_data: List of parsed file data
            repo_url: URL of the repository
            service_name: Name of the service
        """
        data_models = []
        
        # Extract data models from parsed data
        for file_data in parsed_data:
            if file_data.get('data_models'):
                for model in file_data.get('data_models', []):
                    data_models.append({
                        'name': model.get('name', ''),
                        'fields': model.get('fields', []),
                        'orm': model.get('orm', ''),
                        'file_path': file_data.get('path', ''),
                        'service_name': service_name,
                        'repo_url': repo_url
                    })
        
        # Load data models into Neo4j
        if data_models:
            logger.info(f"Loading {len(data_models)} data models for {service_name}")
            
            for model in data_models:
                # Create DataModel node
                query = """
                MERGE (dm:DataModel {name: $name, repo_url: $repo_url})
                SET dm.service_name = $service_name,
                    dm.file_path = $file_path,
                    dm.orm = $orm,
                    dm.fields = $fields
                WITH dm
                MATCH (s:Service {name: $service_name, repository_url: $repo_url})
                MERGE (s)-[:USES]->(dm)
                WITH dm, $file_path as file_path
                MATCH (f:File {path: $file_path, repo_url: $repo_url})
                MERGE (f)-[:CONTAINS]->(dm)
                """
                
                params = {
                    'name': model['name'],
                    'service_name': model['service_name'],
                    'file_path': model['file_path'],
                    'orm': model['orm'],
                    'fields': json.dumps(model['fields']),
                    'repo_url': model['repo_url']
                }
                
                try:
                    await self.db_manager.run_query(query, params)
                except Exception as e:
                    logger.error(f"Error creating data model: {e}")
    
    async def _analyze_cross_service_relationships(self):
        """
        Analyze and create relationships between services.
        """
        logger.info("Analyzing cross-service relationships")
        
        # Find services that communicate with each other (based on imports or API calls)
        query = """
        MATCH (s1:Service)-[:EXPOSES]->(api:ApiEndpoint)
        MATCH (s2:Service)-[:BELONGS_TO]->(f:File)-[:IMPORTS]->(client_file:File)-[:BELONGS_TO]->(s1)
        WHERE s1 <> s2
        MERGE (s2)-[r:COMMUNICATES_WITH]->(s1)
        SET r.type = 'api_call',
            r.last_updated = timestamp()
        """
        
        try:
            await self.db_manager.run_query(query)
            logger.info("Created COMMUNICATES_WITH relationships between services")
        except Exception as e:
            logger.error(f"Error analyzing cross-service relationships: {e}")
    
    async def run_enhanced_ingestion(self):
        """
        Run the enhanced ingestion pipeline.
        """
        logger.info("Starting enhanced knowledge system ingestion")
        
        # Connect to the database
        if not await self.connect_database():
            logger.critical("Failed to connect to database. Aborting ingestion.")
            return
        
        # Process each repository
        for repo_config in self.config.get("repositories", []):
            try:
                await self.ingest_repository(repo_config)
            except Exception as e:
                logger.error(f"Error ingesting repository {repo_config.get('url')}: {e}", exc_info=True)
        
        logger.info("Enhanced knowledge system ingestion completed")


async def run_enhanced_ingestion(config_path: Optional[str] = None) -> None:
    """
    Run the enhanced ingestion pipeline.
    
    Args:
        config_path: Path to configuration file (optional)
    """
    knowledge_system = EnhancedKnowledgeSystem(config_path)
    await knowledge_system.run_enhanced_ingestion()


def main() -> None:
    """
    Main entry point for CLI usage.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhanced Knowledge System Ingestion"
    )
    parser.add_argument(
        "--config", 
        type=str, 
        help="Path to configuration file"
    )
    parser.add_argument(
        "--repos", 
        type=str, 
        nargs='+',
        help="List of repository URLs to ingest (space-separated)"
    )
    
    args = parser.parse_args()
    
    # Create a config dictionary if repos are provided
    config = None
    if args.repos:
        config = {
            "repositories": []
        }
        
        for repo_url in args.repos:
            config["repositories"].append({
                "url": repo_url,
                "service_name": repo_url.split('/')[-1].replace('.git', '')
            })
    
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(config, f)
            temp_config_path = f.name
        
        try:
            asyncio.run(run_enhanced_ingestion(temp_config_path))
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_config_path)
            except:
                pass
    else:
        asyncio.run(run_enhanced_ingestion(args.config))


if __name__ == "__main__":
    main() 