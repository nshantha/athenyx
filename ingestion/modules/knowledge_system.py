"""
Module implementing the enterprise knowledge system.
This handles the core code repository processing and knowledge graph creation.
"""
import logging
import json
import os
from typing import Dict, Any, List, Tuple

from app.db.neo4j_manager import db_manager
from app.core.config import settings
from ingestion.config import ingestion_settings, get_target_extensions
from ingestion.sources.git_loader import GitLoader
from ingestion.parsing.tree_sitter_parser import TreeSitterParser
from ingestion.processing.chunking import chunk_code
from ingestion.processing.embedding import embed_chunks
from ingestion.loading.neo4j_loader import Neo4jLoader
from ingestion.modules.microservices import MicroservicesIngestion
from ingestion.modules.api import ApiExtractor

logger = logging.getLogger(__name__)

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
        # Debug logging for environment variables and settings
        logger.info(f"Debug init: INGEST_REPO_URL from env: '{os.getenv('INGEST_REPO_URL')}'")
        logger.info(f"Debug init: ingestion_settings.ingest_repo_url: '{ingestion_settings.ingest_repo_url}'")
        
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
                await self.db_manager.run_query(query)
                
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
        logger.info(f"Extracted {len(api_definitions)} API endpoints and {len(data_models)} data models from {repo_url}")
        
        # Load API endpoints and data models into the graph
        await self._load_api_and_data_models(api_definitions, data_models, repo_url, service_name)
        
        # Process code chunks and create embeddings
        await self._process_code_chunks(files_content, repo_url, service_name)
        
        # Update repository status
        await self.db_manager.update_repository_status(repo_url, current_commit_sha)
        
        # Analyze cross-service relationships after each repository is ingested
        # This helps build connections incrementally
        await self._analyze_cross_service_relationships()
        
        logger.info(f"Repository {repo_url} ingestion completed.")
    
    def _extract_service_name(self, repo_url):
        """Extract service name from repository URL."""
        if not repo_url:
            return "unknown-service"
            
        # Remove trailing slashes and .git extension
        clean_url = repo_url.rstrip('/').rstrip('.git')
        
        # Get the last part of the URL (the repo name)
        parts = clean_url.split('/')
        return parts[-1]
    
    def _parse_files(self, files_content):
        """
        Parse files based on language detection.
        
        Args:
            files_content: List of tuples containing (file_path, content)
            
        Returns:
            List of parsed file data
        """
        parsed_data = []
        
        # --- Define language mapping ---
        extension_to_language = {
            ".py": "python",
            ".go": "go",
            ".cs": "csharp",
            ".java": "java",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".proto": "protobuf",
            ".md": "markdown",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
        }
        
        # Process each file
        for file_path, content in files_content:
            # Determine language from file extension
            _, ext = os.path.splitext(file_path)
            language = extension_to_language.get(ext.lower())
            
            if not language:
                self.logger.debug(f"Skipping structural parsing for file with unmapped extension: {file_path}")
                continue
                
            try:
                # Use TreeSitterParser to parse the file
                result = TreeSitterParser.parse_file(file_path, content, language)
                if result:
                    result['language'] = language
                    parsed_data.append(result)
                else:
                    # Add basic file entry if parsing returned None
                    parsed_data.append({"path": file_path, "language": language, "parse_error": True})
                    
            except Exception as e:
                self.logger.error(f"Error parsing file {file_path} ({language}): {e}", exc_info=True)
                parsed_data.append({"path": file_path, "language": language, "parse_error": True})
                
        self.logger.info(f"Successfully parsed (or attempted) {len(parsed_data)} files.")
        return parsed_data
        
    def _handle_special_file_types(self, file_path, content, language):
        """
        Handle special file types like documentation, protocol buffers, and configuration files.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            language: Detected language/file type
            
        Returns:
            Parsed file data in a format compatible with the knowledge graph
        """
        # Use our new SimpleParser for parsing special file types
        from ingestion.parsing.simple_parser import SimpleParser
        from ingestion.parsing.tree_sitter_parser import TreeSitterParser
        
        try:
            # Use SimpleParser to parse the file
            simple_parser = SimpleParser(language)
            result = simple_parser.parse(file_path, content)
            
            # Add language field
            result["language"] = language
            
            # Return the parsed result
            return result
            
        except Exception as e:
            self.logger.error(f"Error parsing special file {file_path} ({language}): {e}", exc_info=True)
            # Return basic structure if parsing failed
            return {
                "path": file_path,
                "language": language,
                "content": content,
                "functions": [],
                "classes": [],
                "relationships": [],
                "parse_error": True
            }
    
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
            await self.db_manager.run_query(query, params)
            logger.info(f"Created/updated Repository node for {repo_url}")
        except Exception as e:
            logger.error(f"Failed to create Repository node: {e}")
            
    async def _process_code_chunks(self, files_content, repo_url, service_name):
        """
        Process code files into chunks and create embeddings.
        Uses the same successful approach as the original ingestion_pipeline.
        
        Args:
            files_content: List of tuples containing (file_path, content)
            repo_url: URL of the repository
            service_name: Name of the service/repository
        """
        logger.info(f"Processing code chunks for {repo_url}")
        
        try:
            # --- Parse files using TreeSitterParser (like in original pipeline) ---
            extension_to_language = {
                ".py": "python",
                ".go": "go",
                ".cs": "csharp",
                ".java": "java",
                ".js": "javascript",
                ".jsx": "javascript",
                ".ts": "typescript",
                ".tsx": "typescript",
                ".md": "markdown",
                ".txt": "text",
                ".json": "json",
                ".yml": "yaml",
                ".yaml": "yaml",
            }
            
            # Step 1: Parse files with TreeSitterParser for structural data
            parsed_data = []
            for file_path, content in files_content:
                # Skip very large files and binary files
                if len(content) > 1000000 or '\0' in content:
                    logger.warning(f"Skipping large or binary file: {file_path}")
                    continue
                
                # Determine language from file extension
                _, ext = os.path.splitext(file_path)
                language = extension_to_language.get(ext.lower())
                
                if not language:
                    logger.debug(f"Skipping structural parsing for file with unmapped extension: {file_path}")
                    # Add a basic file entry for completeness
                    parsed_data.append({"path": file_path, "language": "unknown", "parse_error": True})
                    continue
                
                try:
                    # Use TreeSitterParser (same as original pipeline)
                    result = TreeSitterParser.parse_file(file_path, content, language)
                    if result:
                        result['language'] = language
                        parsed_data.append(result)
                    else:
                        parsed_data.append({"path": file_path, "language": language, "parse_error": True})
                except Exception as e:
                    logger.error(f"Error parsing file {file_path} ({language}): {e}", exc_info=True)
                    parsed_data.append({"path": file_path, "language": language, "parse_error": True})
            
            # Step 2: Create chunks from the parsed data
            all_chunks = chunk_code(parsed_data, "auto")
            logger.info(f"Created {len(all_chunks)} code chunks from {len(files_content)} files")
            
            # Step 3: Create embeddings for the chunks
            chunks_with_embeddings = await embed_chunks(all_chunks)
            logger.info(f"Created embeddings for {len(chunks_with_embeddings)} code chunks")
            
            # Step 4: Load into Neo4j (using the original Neo4jLoader)
            neo4j_loader = Neo4jLoader(repo_url=repo_url)
            await neo4j_loader.load_data(parsed_data, chunks_with_embeddings)
            logger.info(f"Loaded code chunks and embeddings into Neo4j for {repo_url}")
            
            # Step 5: Create additional relationships between code chunks and repository/service
            # (This is specific to the comprehensive pipeline)
            query = """
            MATCH (cc:CodeChunk)
            WHERE cc.repo_url = $repo_url
            WITH cc
            MATCH (r:Repository {url: $repo_url})
            MATCH (s:Service {name: $service_name})
            MERGE (cc)-[:BELONGS_TO]->(r)
            MERGE (cc)-[:BELONGS_TO]->(s)
            """
            
            params = {"repo_url": repo_url, "service_name": service_name}
            await self.db_manager.run_query(query, params)
            
            # Step 6: Verify CONTAINS relationships were created
            check_query = """
            MATCH (parent)-[:CONTAINS]->(cc:CodeChunk)
            WHERE cc.repo_url = $repo_url
            RETURN labels(parent) as parent_type, count(*) as rel_count
            """
            
            check_params = {"repo_url": repo_url}
            rel_result = await self.db_manager.run_query(check_query, check_params)
            
            for r in rel_result:
                logger.info(f"Created {r['rel_count']} CONTAINS relationships from {r['parent_type']} nodes to CodeChunk nodes")
            
            # If no CONTAINS relationships, log a warning
            if not rel_result:
                logger.warning("No CONTAINS relationships were created between parents and CodeChunks!")
            
        except Exception as e:
            logger.error(f"Error processing code chunks for {repo_url}: {e}", exc_info=True)
            raise

    async def ingest_microservices(self, repo_path=None, repo_url=None):
        """
        Analyze microservices architecture and relationships.
        
        Args:
            repo_path: Path to repository with microservices
            repo_url: URL of the microservices repository to clone
        """
        repo_path = repo_path or os.getenv("REPO_PATH", "./cloned_repo")
        
        try:
            ingestion = MicroservicesIngestion(
                repo_path=repo_path,
                neo4j_uri=None,
                neo4j_user=None, 
                neo4j_password=None,
                repo_url=repo_url
            )
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
            # 1. Find API dependencies between services
            query = """
            // Match API endpoints and potential callers
            MATCH (s1:Service)-[:EXPOSES]->(api:ApiEndpoint)
            MATCH (s2:Service)<-[:BELONGS_TO]-(func:Function)
            WHERE s1 <> s2
            AND (
                // Look for HTTP client calls that might reference this endpoint
                func.code CONTAINS 'http' OR 
                func.code CONTAINS 'fetch' OR 
                func.code CONTAINS 'axios' OR
                func.code CONTAINS 'request' OR
                func.code CONTAINS 'RestTemplate' OR
                func.code CONTAINS 'WebClient' OR
                func.code CONTAINS 'HttpClient'
            )
            // Create potential dependency relationships
            WITH api, func, s1, s2
            WHERE func.code CONTAINS api.name OR 
                  func.code CONTAINS REPLACE(api.name, '_', '-') OR
                  func.code CONTAINS api.api_path OR
                  func.code CONTAINS s1.name
            MERGE (func)-[:MAY_CALL]->(api)
            
            // Also create a service-to-service relationship
            MERGE (s2)-[r:CALLS_SERVICE]->(s1)
            ON CREATE SET r.first_detected = datetime(), r.count = 1
            ON MATCH SET r.count = r.count + 1, r.last_updated = datetime()
            
            RETURN count(*) as relationships
            """
            
            result = await self.db_manager.run_query(query)
            count = result[0]['relationships'] if result else 0
            logger.info(f"Identified {count} potential cross-service API dependencies")
            
            # 2. Find shared data models between services
            query = """
            // Match data models with similar names across services
            MATCH (s1:Service)-[:USES_MODEL]->(dm1:DataModel)
            MATCH (s2:Service)-[:USES_MODEL]->(dm2:DataModel)
            WHERE s1 <> s2
            AND dm1.name = dm2.name
            MERGE (dm1)-[:SIMILAR_TO]->(dm2)
            
            // Create a service-to-service relationship for shared models
            MERGE (s1)-[r:SHARES_MODEL_WITH]->(s2)
            ON CREATE SET r.first_detected = datetime(), r.count = 1
            ON MATCH SET r.count = r.count + 1, r.last_updated = datetime()
            
            RETURN count(*) as relationships
            """
            
            result = await self.db_manager.run_query(query)
            count = result[0]['relationships'] if result else 0
            logger.info(f"Identified {count} potential shared data models across services")
            
            # Add more relationship types as needed...
            
        except Exception as e:
            logger.error(f"Error during cross-service relationship analysis: {e}", exc_info=True)

    # Additional methods from the original file can be added here
    # _extract_data_models_with_tree_sitter, _extract_api_and_data_models, etc.
    
    async def run_comprehensive_ingestion(self):
        """
        Run the comprehensive ingestion process for all configured repositories.
        This is the main entry point for the ingestion pipeline.
        """
        try:
            # 1. Connect to the database
            await self.connect_database()
            
            # 2. Process each repository in the configuration
            repositories = self.config.get("repositories", [])
            if repositories:
                for repo_config in repositories:
                    logger.info(f"Starting ingestion for repository: {repo_config.get('url')}")
                    await self.ingest_code_repository(repo_config)
            elif ingestion_settings.ingest_repo_url:
                # Use the repository URL from environment settings if none in config
                repo_url = ingestion_settings.ingest_repo_url
                service_name = self._extract_service_name(repo_url)
                repo_config = {
                    "url": repo_url,
                    "service_name": service_name,
                    "branch": ingestion_settings.ingest_repo_branch
                }
                logger.info(f"Starting ingestion for repository from env settings: {repo_url}")
                await self.ingest_code_repository(repo_config)
            else:
                logger.warning("No repositories configured for ingestion")
                
            # 3. Analyze cross-service relationships
            await self._analyze_cross_service_relationships()
            
            logger.info("Comprehensive ingestion completed successfully")
            
        except Exception as e:
            logger.error(f"Error during comprehensive ingestion: {e}", exc_info=True)
            raise

    def _extract_api_and_data_models(self, parsed_data, repo_url):
        """
        Extract API definitions and data models from parsed code.
        
        Args:
            parsed_data: Parsed code data
            repo_url: Repository URL
            
        Returns:
            Tuple of (api_definitions, data_models)
        """
        return ApiExtractor.extract_api_and_data_models(parsed_data, repo_url)
        
    async def _load_api_and_data_models(self, api_definitions, data_models, repo_url, service_name):
        """
        Load API definitions and data models into the graph database.
        
        Args:
            api_definitions: List of API endpoint definitions
            data_models: List of data model definitions
            repo_url: Repository URL
            service_name: Service name
        """
        if not api_definitions and not data_models:
            logger.debug("No API endpoints or data models to load")
            return
            
        # First create a Service node if it doesn't exist
        query = """
        MERGE (s:Service {name: $service_name})
        SET s.repo_url = $repo_url,
            s.last_updated = datetime()
        RETURN s
        """
        params = {
            "service_name": service_name,
            "repo_url": repo_url
        }
        await self.db_manager.run_query(query, params)
        logger.info(f"Created/updated Service node for {service_name}")
        
        # Create API endpoints
        for api in api_definitions:
            # Create the API endpoint node
            query = """
            MERGE (api:ApiEndpoint {
                name: $name,
                path: $path,
                method: $method,
                file_path: $file_path,
                framework: $framework,
                repo_url: $repo_url
            })
            SET api.code = $code,
                api.params = $params,
                api.return_type = $return_type,
                api.last_updated = datetime()
            
            WITH api
            
            // Create relationship to Service
            MATCH (s:Service {name: $service_name})
            MERGE (s)-[:EXPOSES]->(api)
            
            // Create relationship to Repository
            MATCH (r:Repository {url: $repo_url})
            MERGE (api)-[:BELONGS_TO]->(r)
            
            RETURN api
            """
            params = {
                "name": api.get("name", ""),
                "path": api.get("path", ""),
                "method": api.get("method", "GET"),
                "file_path": api.get("file_path", ""),
                "framework": api.get("framework", ""),
                "code": api.get("code", ""),
                "params": json.dumps(api.get("params", [])),
                "return_type": api.get("return_type", ""),
                "repo_url": repo_url,
                "service_name": service_name
            }
            
            try:
                await self.db_manager.run_query(query, params)
            except Exception as e:
                logger.error(f"Error loading API endpoint {api.get('name')}: {e}")
        
        # Create data models
        for model in data_models:
            # Create the DataModel node
            query = """
            MERGE (dm:DataModel {
                name: $name,
                type: $type,
                file_path: $file_path,
                repo_url: $repo_url
            })
            SET dm.code = $code,
                dm.fields = $fields,
                dm.last_updated = datetime()
            
            WITH dm
            
            // Create relationship to Service
            MATCH (s:Service {name: $service_name})
            MERGE (s)-[:USES_MODEL]->(dm)
            
            // Create relationship to Repository
            MATCH (r:Repository {url: $repo_url})
            MERGE (dm)-[:BELONGS_TO]->(r)
            
            RETURN dm
            """
            params = {
                "name": model.get("name", ""),
                "type": model.get("type", ""),
                "file_path": model.get("file_path", ""),
                "code": model.get("code", ""),
                "fields": json.dumps(model.get("fields", [])),
                "repo_url": repo_url,
                "service_name": service_name
            }
            
            try:
                await self.db_manager.run_query(query, params)
            except Exception as e:
                logger.error(f"Error loading data model {model.get('name')}: {e}")
                
        logger.info(f"Loaded {len(api_definitions)} API endpoints and {len(data_models)} data models for {service_name}") 