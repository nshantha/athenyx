"""
Simple parser for file types that don't need complex AST parsing.
"""
import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class SimpleParser:
    """A simple parser for file formats that don't need complex AST parsing."""
    
    def __init__(self, language):
        """Initialize the simple parser."""
        self.language = language
    
    def parse(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parse the source code into a simple structure.
        For formats like markdown, yaml, json, and proto, we just need the text content.
        
        Args:
            file_path: Path to the file being parsed
            content: The source code to parse
            
        Returns:
            A simple structure with the parsed content
        """
        try:
            if self.language == 'protobuf':
                return self._parse_protobuf(file_path, content)
            elif self.language == 'markdown':
                return self._parse_markdown(file_path, content)
            elif self.language in ['yaml', 'yml']:
                return self._parse_yaml(file_path, content)
            elif self.language == 'json':
                return self._parse_json(file_path, content)
            else:
                # Generic parser for other simple file types
                return {
                    'path': file_path,
                    'language': self.language,
                    'content': content,
                    'functions': [],
                    'classes': [],
                    'imports': [],
                    'is_documentation': False
                }
        except Exception as e:
            logger.error(f"Error parsing {file_path} with {self.language} parser: {e}")
            # Return a basic structure on error
            return {
                'path': file_path,
                'language': self.language,
                'content': content,
                'functions': [],
                'classes': [],
                'parse_error': True
            }
    
    def _parse_protobuf(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parse protobuf file to extract messages and services.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            
        Returns:
            Dictionary with parsed protobuf structure
        """
        try:
            logger.info(f"Parsing protobuf file: {file_path}")
            
            # Extract message definitions with more robust regex
            messages = []
            try:
                # First try with the standard pattern
                message_pattern = r'message\s+(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
                for name, body in re.findall(message_pattern, content, re.DOTALL):
                    try:
                        # Get line numbers
                        message_start = content.find(f"message {name}")
                        message_end = content.find("}", message_start) + 1
                        start_line = content[:message_start].count('\n') + 1
                        end_line = content[:message_end].count('\n') + 1
                        
                        # Add to messages list
                        messages.append({
                            'name': name,
                            'unique_id': f"{file_path}::{name}",
                            'start_line': start_line,
                            'end_line': end_line,
                            'fields': self._extract_proto_fields(body)
                        })
                    except Exception as e:
                        logger.warning(f"Error processing message {name} in {file_path}: {e}")
                
                logger.debug(f"Found {len(messages)} messages in {file_path}")
            except Exception as e:
                logger.warning(f"Error extracting messages from {file_path}: {e}")
            
            # Extract service definitions with more robust regex
            services = []
            try:
                # First try with the standard pattern
                service_pattern = r'service\s+(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
                for name, body in re.findall(service_pattern, content, re.DOTALL):
                    try:
                        # Get line numbers
                        service_start = content.find(f"service {name}")
                        service_end = content.find("}", service_start) + 1
                        start_line = content[:service_start].count('\n') + 1
                        end_line = content[:service_end].count('\n') + 1
                        
                        # Add to services list
                        services.append({
                            'name': name,
                            'unique_id': f"{file_path}::{name}",
                            'start_line': start_line,
                            'end_line': end_line,
                            'methods': self._extract_proto_methods(body)
                        })
                    except Exception as e:
                        logger.warning(f"Error processing service {name} in {file_path}: {e}")
                
                logger.debug(f"Found {len(services)} services in {file_path}")
            except Exception as e:
                logger.warning(f"Error extracting services from {file_path}: {e}")
            
            # Return parsed data
            result = {
                'path': file_path,
                'language': 'protobuf',
                'content': content,
                'functions': [],  # No traditional functions in proto
                'classes': messages + services,  # Treat both messages and services as "classes"
                'imports': self._extract_proto_imports(content),
                'messages': messages,
                'services': services,
                'is_documentation': False,
                'is_data_model': len(messages) > 0,
                'is_api': len(services) > 0
            }
            
            logger.info(f"Successfully parsed protobuf file {file_path}: {len(messages)} messages, {len(services)} services")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing protobuf file {file_path}: {e}", exc_info=True)
            # Return a basic structure on error
            return {
                'path': file_path,
                'language': 'protobuf',
                'content': content,
                'functions': [],
                'classes': [],
                'parse_error': True
            }
    
    def _extract_proto_fields(self, message_body: str) -> List[Dict[str, str]]:
        """Extract fields from a protobuf message."""
        try:
            field_pattern = r'\s*(repeated|optional|required)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)'
            fields = []
            
            for modifier, field_type, name, number in re.findall(field_pattern, message_body):
                fields.append({
                    'name': name,
                    'type': field_type,
                    'modifier': modifier if modifier else 'optional',  # Default is optional in proto3
                    'number': number
                })
            
            return fields
        except Exception as e:
            logger.warning(f"Error extracting proto fields: {e}")
            return []
    
    def _extract_proto_methods(self, service_body: str) -> List[Dict[str, str]]:
        """Extract methods from a protobuf service."""
        try:
            method_pattern = r'\s*rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)'
            methods = []
            
            for name, request_type, response_type in re.findall(method_pattern, service_body):
                methods.append({
                    'name': name,
                    'request_type': request_type,
                    'response_type': response_type
                })
            
            return methods
        except Exception as e:
            logger.warning(f"Error extracting proto methods: {e}")
            return []
    
    def _extract_proto_imports(self, content: str) -> List[Dict[str, str]]:
        """Extract imports from a protobuf file."""
        try:
            import_pattern = r'import\s+"([^"]+)";'
            imports = []
            
            for path in re.findall(import_pattern, content):
                imports.append({
                    'path': path,
                    'name': path.split('/')[-1],
                    'is_system': path.startswith('google/')
                })
            
            return imports
        except Exception as e:
            logger.warning(f"Error extracting proto imports: {e}")
            return []
    
    def _parse_markdown(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Parse markdown file to extract sections and metadata.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            
        Returns:
            Dictionary with parsed markdown structure
        """
        # Extract headers and create a simple section structure
        header_pattern = r'^(#+)\s+(.+)$'
        sections = []
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines):
            header_match = re.match(header_pattern, line)
            
            if header_match:
                # Save previous section if exists
                if current_section:
                    current_section['content'] = '\n'.join(current_content)
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    'title': title,
                    'level': level,
                    'start_line': i + 1,
                    'unique_id': f"section_{title.lower().replace(' ', '_')}_chunk_{len(sections)}"
                }
                current_content = []
            elif current_section:
                current_content.append(line)
        
        # Add the last section
        if current_section:
            current_section['content'] = '\n'.join(current_content)
            current_section['end_line'] = len(lines)
            sections.append(current_section)
        
        return {
            'path': file_path,
            'language': 'markdown',
            'content': content,
            'functions': [],
            'classes': [],
            'imports': [],
            'sections': sections,
            'is_documentation': True
        }
    
    def _parse_yaml(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse YAML file."""
        return {
            'path': file_path,
            'language': 'yaml',
            'content': content,
            'functions': [],
            'classes': [],
            'imports': [],
            'is_documentation': False,
            'is_config': True
        }
    
    def _parse_json(self, file_path: str, content: str) -> Dict[str, Any]:
        """Parse JSON file."""
        # Try to extract key-value pairs for top-level objects
        json_keys = []
        key_pattern = r'"([^"]+)"\s*:'
        
        for i, key in enumerate(re.findall(key_pattern, content)):
            # Get approximate line number
            key_pos = content.find(f'"{key}"')
            start_line = content[:key_pos].count('\n') + 1
            
            # Add as a pseudo-function for better indexing
            json_keys.append({
                'name': key,
                'unique_id': f"json_key::{key}",
                'start_line': start_line,
                'end_line': start_line + 1  # Approximate
            })
        
        return {
            'path': file_path,
            'language': 'json',
            'content': content,
            'functions': json_keys,  # Represent top-level keys as functions
            'classes': [],
            'imports': [],
            'is_documentation': False,
            'is_config': True
        } 