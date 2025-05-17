"""
Enhanced Neo4j Loader

This module integrates the knowledge_graph builder pattern with the ingestion system's
efficient loading capabilities to provide a comprehensive loading solution.
"""

import logging
import os
from typing import List, Dict, Any, Optional, Union

from app.db.neo4j_manager import db_manager
from ingestion.loading.neo4j_loader import Neo4jLoader
from ingestion.schema import RELATIONSHIP_TYPES, get_node_types, get_relationship_types

logger = logging.getLogger(__name__)


class EnhancedLoader:
    """
    Enhanced loader that combines the builder pattern from knowledge_graph
    with the efficient loading capabilities of the ingestion system.
    """

    def __init__(self, repo_url: str):
        """
        Initialize the enhanced loader.
        
        Args:
            repo_url: URL of the repository being processed
        """
        self.repo_url = repo_url
        self.base_loader = Neo4jLoader(repo_url)
        self.created_entities = {}  # Track created entities to avoid duplicates
        
    async def load_data(self, parsed_data: List[Dict[str, Any]], chunks_with_embeddings: List[Dict[str, Any]]):
        """
        Load parsed data and chunks with embeddings into Neo4j.
        
        Args:
            parsed_data: List of parsed file data
            chunks_with_embeddings: List of code chunks with embeddings
        """
        # Use the base loader for the core loading functionality
        await self.base_loader.load_data(parsed_data, chunks_with_embeddings)
        
        # Enhance with additional relationships and semantic connections
        await self._enhance_relationships(parsed_data)
        
    async def _enhance_relationships(self, parsed_data: List[Dict[str, Any]]):
        """
        Enhance the knowledge graph with additional relationships based on parsed data.
        
        Args:
            parsed_data: List of parsed file data
        """
        logger.info("Enhancing knowledge graph with additional relationships")
        
        # Process each file to extract and create additional relationships
        for file_data in parsed_data:
            if file_data.get('parse_error'):
                continue
                
            file_path = file_data['path']
            
            # Extract function calls and create CALLS relationships
            await self._process_function_calls(file_data)
            
            # Extract imports and create IMPORTS relationships
            await self._process_imports(file_data)
            
            # Extract inheritance and create INHERITS_FROM relationships
            await self._process_inheritance(file_data)
            
            # Extract implementations and create IMPLEMENTS relationships
            await self._process_implementations(file_data)
    
    async def _process_function_calls(self, file_data: Dict[str, Any]):
        """
        Process function calls and create CALLS relationships.
        
        Args:
            file_data: Parsed file data
        """
        # Extract function calls if available in the parsed data
        function_calls = file_data.get('function_calls', [])
        
        for call in function_calls:
            source_name = call.get('source_name')
            target_name = call.get('target_name')
            
            if not source_name or not target_name:
                continue
                
            # Create CALLS relationship directly using name properties
            create_rel_query = """
            MATCH (source:Function {name: $source_name, repo_url: $repo_url})
            MATCH (target:Function {name: $target_name, repo_url: $repo_url})
            MERGE (source)-[r:CALLS {
                repo_url: $repo_url,
                line: $line,
                count: $count
            }]->(target)
            RETURN r
            """
            
            await db_manager.run_query(
                create_rel_query,
                {
                    "source_name": source_name,
                    "target_name": target_name,
                    "repo_url": self.repo_url,
                    "line": call.get('line', 0),
                    "count": call.get('count', 1)
                }
            )
    
    async def _process_imports(self, file_data: Dict[str, Any]):
        """
        Process imports and create IMPORTS relationships.
        
        Args:
            file_data: Parsed file data
        """
        # Extract imports if available in the parsed data
        imports = file_data.get('imports', [])
        
        if not imports:
            return
            
        source_path = file_data['path']
        
        # Get all files in the repository to match against imports
        # This is more robust than relying on exact path matches
        get_files_query = """
        MATCH (f:File {repo_url: $repo_url})
        RETURN f.path as path, f.language as language
        """
        
        result = await db_manager.run_query(get_files_query, {"repo_url": self.repo_url})
        repo_files = {row['path']: row['language'] for row in result}
        
        for imp in imports:
            target_path = imp.get('path')
            import_name = imp.get('name', '')
            
            if not target_path:
                continue
            
            # Try to find the actual file that corresponds to this import
            matched_path = self._resolve_import_path(source_path, target_path, import_name, repo_files)
            
            if matched_path:
                # Create IMPORTS relationship with the resolved path
                create_rel_query = """
                MATCH (source:File {path: $source_path, repo_url: $repo_url})
                MATCH (target:File {path: $matched_path, repo_url: $repo_url})
                MERGE (source)-[r:IMPORTS {
                    repo_url: $repo_url,
                    line: $line,
                    import_name: $import_name
                }]->(target)
                RETURN r
                """
                
                await db_manager.run_query(
                    create_rel_query,
                    {
                        "source_path": source_path,
                        "matched_path": matched_path,
                        "repo_url": self.repo_url,
                        "line": imp.get('line', 0),
                        "import_name": import_name
                    }
                )
            else:
                # Log that we couldn't resolve this import
                logger.debug(f"Could not resolve import path '{target_path}' from '{source_path}' in repo {self.repo_url}")
    
    def _resolve_import_path(self, source_path: str, target_path: str, import_name: str, repo_files: Dict[str, str]) -> Optional[str]:
        """
        Resolve an import path to an actual file path in the repository.
        
        Args:
            source_path: Path of the source file
            target_path: Raw import path from the parser
            import_name: Name of the imported module/package
            repo_files: Dictionary of all files in the repository
            
        Returns:
            Resolved file path if found, None otherwise
        """
        # If the target path is already an exact match, return it
        if target_path in repo_files:
            return target_path
            
        # Handle relative imports in Python
        if target_path.startswith('.'):
            # Get the directory of the source file
            source_dir = os.path.dirname(source_path)
            # Count the number of dots to determine how many directories to go up
            dot_count = 0
            for char in target_path:
                if char == '.':
                    dot_count += 1
                else:
                    break
                    
            # Go up dot_count-1 directories (first dot is current directory)
            for _ in range(dot_count - 1):
                source_dir = os.path.dirname(source_dir)
                
            # Remove the dots from the target path
            clean_target = target_path[dot_count:]
            if clean_target.startswith('/'):
                clean_target = clean_target[1:]
                
            # Construct the potential path
            potential_path = os.path.join(source_dir, clean_target)
            
            # Check if this file exists
            if potential_path in repo_files:
                return potential_path
            
            # Try with .py extension for Python files
            if potential_path + '.py' in repo_files:
                return potential_path + '.py'
                
        # For Python absolute imports, try different path combinations
        if source_path.endswith('.py'):
            # Try with different path variations
            variations = [
                target_path,
                target_path + '.py',
                target_path.replace('.', '/') + '.py',
                target_path.replace('.', '/') + '/__init__.py'
            ]
            
            for variation in variations:
                if variation in repo_files:
                    return variation
                    
        # For Go imports, try to match based on the package name
        if source_path.endswith('.go') and import_name:
            # Try to find Go files that might match this import
            for file_path, language in repo_files.items():
                if language == 'go' and file_path.endswith('.go'):
                    # Check if the file path contains the import name
                    path_parts = file_path.split('/')
                    if import_name in path_parts:
                        # If the file is in a directory with the import name, it's likely a match
                        return file_path
                        
        # For JavaScript/TypeScript imports
        if source_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
            # Try with different extensions
            js_extensions = ['.js', '.jsx', '.ts', '.tsx']
            for ext in js_extensions:
                if target_path + ext in repo_files:
                    return target_path + ext
                    
            # Try with index files
            for ext in js_extensions:
                index_path = os.path.join(target_path, 'index' + ext)
                if index_path in repo_files:
                    return index_path
                    
        # For Java imports, try to match package structure
        if source_path.endswith('.java'):
            java_path = target_path.replace('.', '/') + '.java'
            if java_path in repo_files:
                return java_path
                
        # For C# imports, try to match namespace structure
        if source_path.endswith('.cs'):
            cs_path = target_path.replace('.', '/') + '.cs'
            if cs_path in repo_files:
                return cs_path
                
        # Could not resolve the import path
        return None
    
    async def _process_inheritance(self, file_data: Dict[str, Any]):
        """
        Process class inheritance and create INHERITS_FROM relationships.
        
        Args:
            file_data: Parsed file data
        """
        # Extract classes with inheritance information
        classes = file_data.get('classes', [])
        
        for cls in classes:
            if not cls.get('superclasses'):
                continue
                
            source_name = cls.get('name')
            if not source_name:
                continue
                
            for superclass in cls.get('superclasses', []):
                # Create INHERITS_FROM relationship directly using name properties
                create_rel_query = """
                MATCH (source:Class {name: $source_name, repo_url: $repo_url})
                MATCH (target:Class {name: $target_name, repo_url: $repo_url})
                MERGE (source)-[r:INHERITS_FROM {repo_url: $repo_url}]->(target)
                RETURN r
                """
                
                await db_manager.run_query(
                    create_rel_query,
                    {
                        "source_name": source_name,
                        "target_name": superclass,
                        "repo_url": self.repo_url
                    }
                )
    
    async def _process_implementations(self, file_data: Dict[str, Any]):
        """
        Process interface implementations and create IMPLEMENTS relationships.
        
        Args:
            file_data: Parsed file data
        """
        # Extract classes with interface implementation information
        classes = file_data.get('classes', [])
        
        for cls in classes:
            if not cls.get('interfaces'):
                continue
                
            source_name = cls.get('name')
            if not source_name:
                continue
                
            for interface in cls.get('interfaces', []):
                # Create IMPLEMENTS relationship directly using name properties
                create_rel_query = """
                MATCH (source:Class {name: $source_name, repo_url: $repo_url})
                MATCH (target:Class {name: $target_name, repo_url: $repo_url})
                MERGE (source)-[r:IMPLEMENTS {repo_url: $repo_url}]->(target)
                RETURN r
                """
                
                await db_manager.run_query(
                    create_rel_query,
                    {
                        "source_name": source_name,
                        "target_name": interface,
                        "repo_url": self.repo_url
                    }
                )
    
    async def create_relationship(self, source_id: str, target_id: str, rel_type: str, properties: Optional[Dict] = None):
        """
        Create a relationship between two nodes.
        
        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            rel_type: Type of relationship
            properties: Optional properties for the relationship
        """
        # This method is kept for backward compatibility but is no longer used
        # Relationships are now created directly in each method using node properties
        logger.warning("The create_relationship method is deprecated. Use direct Cypher queries with node properties instead.")

    def _extract_language_from_extension(self, file_path: str) -> str:
        """
        Extract language from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or "unknown"
        """
        _, ext = os.path.splitext(file_path)
        extension = ext.lower()
        
        language_map = {
            ".py": "python",
            ".go": "go",
            ".java": "java",
            ".cs": "csharp",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".sh": "shell",
            ".rb": "ruby",
            ".php": "php",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".sql": "sql"
        }
        
        return language_map.get(extension, "unknown") 