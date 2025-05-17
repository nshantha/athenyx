"""
Enhanced Parser Module

This module combines the tree-sitter parsing capabilities of the ingestion system
with additional semantic extraction inspired by the knowledge_graph approach.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Tuple

from ingestion.parsing.tree_sitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)


class EnhancedParser:
    """
    Enhanced parser that combines tree-sitter parsing with additional semantic extraction.
    """
    
    @staticmethod
    def parse_file(file_path: str, content: str, language: str) -> Dict[str, Any]:
        """
        Parse a file and extract enhanced semantic information.
        
        Args:
            file_path: Path to the file
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            Dictionary containing parsed file data with enhanced semantic information
        """
        # Use the tree-sitter parser for basic structure extraction
        parsed_data = TreeSitterParser.parse_file(file_path, content, language)
        
        if not parsed_data or parsed_data.get('parse_error'):
            return parsed_data or {"path": file_path, "parse_error": True}
        
        # Make sure language is set in the parsed data
        parsed_data['language'] = language
        
        # Enhance with additional semantic information
        enhanced_data = EnhancedParser._enhance_parsed_data(parsed_data, content, language)
        
        return enhanced_data
    
    @staticmethod
    def _enhance_parsed_data(parsed_data: Dict[str, Any], content: str, language: str) -> Dict[str, Any]:
        """
        Enhance parsed data with additional semantic information.
        
        Args:
            parsed_data: Parsed file data from tree-sitter
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            Enhanced parsed data
        """
        # Start with the original parsed data
        enhanced_data = parsed_data.copy()
        
        # Extract imports
        imports = EnhancedParser._extract_imports(content, language)
        if imports:
            enhanced_data['imports'] = imports
        
        # Extract function calls
        function_calls = EnhancedParser._extract_function_calls(parsed_data, content, language)
        if function_calls:
            enhanced_data['function_calls'] = function_calls
        
        # Extract inheritance relationships
        inheritance = EnhancedParser._extract_inheritance(parsed_data, content, language)
        if inheritance:
            # Update class information with inheritance data
            for cls in enhanced_data.get('classes', []):
                cls_name = cls.get('name')
                if cls_name in inheritance:
                    cls['superclasses'] = inheritance[cls_name].get('superclasses', [])
                    cls['interfaces'] = inheritance[cls_name].get('interfaces', [])
        
        # Extract API endpoints (if applicable)
        api_endpoints = EnhancedParser._extract_api_endpoints(parsed_data, content, language)
        if api_endpoints:
            enhanced_data['api_endpoints'] = api_endpoints
        
        # Extract data models (if applicable)
        data_models = EnhancedParser._extract_data_models(parsed_data, content, language)
        if data_models:
            enhanced_data['data_models'] = data_models
        
        return enhanced_data
    
    @staticmethod
    def _extract_imports(content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract imports from file content.
        
        Args:
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            List of imports
        """
        imports = []
        import re
        
        if language == 'python':
            # Match both 'import x' and 'from x import y'
            import_patterns = [
                r'^\s*import\s+([a-zA-Z0-9_.,\s]+)',  # import x, y, z
                r'^\s*from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_.,\s*]+)'  # from x import y, z
            ]
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                for pattern in import_patterns:
                    matches = re.match(pattern, line)
                    if matches:
                        if len(matches.groups()) == 1:
                            # 'import x, y, z' case
                            modules = [m.strip() for m in matches.group(1).split(',')]
                            for module in modules:
                                imports.append({
                                    'name': module,
                                    'path': module,  # Keep the original module name for resolution
                                    'line': i + 1
                                })
                        else:
                            # 'from x import y, z' case
                            module = matches.group(1)
                            imported_items = [m.strip() for m in matches.group(2).split(',')]
                            for item in imported_items:
                                if item == '*':
                                    imports.append({
                                        'name': f"{module}.*",
                                        'path': module,
                                        'line': i + 1
                                    })
                                else:
                                    imports.append({
                                        'name': item,
                                        'path': module,  # Store the module path for resolution
                                        'line': i + 1,
                                        'full_name': f"{module}.{item}"  # Store the full import path
                                    })
        
        elif language == 'go':
            # Handle Go imports
            import_pattern = r'^\s*import\s+\(\s*$'
            import_line_pattern = r'^\s*(?:"([^"]+)"|([a-zA-Z0-9_]+)\s+"([^"]+)")'
            single_import_pattern = r'^\s*import\s+(?:"([^"]+)"|([a-zA-Z0-9_]+)\s+"([^"]+)")'
            
            lines = content.split('\n')
            in_import_block = False
            
            for i, line in enumerate(lines):
                if not in_import_block:
                    # Check for import block start
                    if re.match(import_pattern, line):
                        in_import_block = True
                        continue
                    
                    # Check for single-line import
                    single_match = re.match(single_import_pattern, line)
                    if single_match:
                        # Handle both "package" and alias "package" formats
                        package = single_match.group(1) or single_match.group(3)
                        alias = single_match.group(2) or package.split('/')[-1]
                        
                        imports.append({
                            'name': alias,
                            'path': package,
                            'line': i + 1,
                            'alias': alias if single_match.group(2) else None
                        })
                else:
                    # Check for import block end
                    if line.strip() == ')':
                        in_import_block = False
                        continue
                    
                    # Extract package from import line
                    import_match = re.match(import_line_pattern, line)
                    if import_match:
                        # Handle both "package" and alias "package" formats
                        package = import_match.group(1) or import_match.group(3)
                        alias = import_match.group(2) or package.split('/')[-1]
                        
                        imports.append({
                            'name': alias,
                            'path': package,
                            'line': i + 1,
                            'alias': alias if import_match.group(2) else None
                        })
        
        elif language == 'javascript' or language == 'typescript':
            # Handle JavaScript/TypeScript imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                # ES6 import with named import
                match = re.match(r'^\s*import\s+([a-zA-Z0-9_]+)\s+from\s+[\'"]([^\'"]+)[\'"]', line)
                if match:
                    name = match.group(1)
                    module = match.group(2)
                    imports.append({
                        'name': name,
                        'path': module,
                        'line': i + 1
                    })
                    continue
                
                # ES6 import with destructuring
                match = re.match(r'^\s*import\s+\{\s*([^}]+)\s*\}\s+from\s+[\'"]([^\'"]+)[\'"]', line)
                if match:
                    items = [item.strip() for item in match.group(1).split(',')]
                    module = match.group(2)
                    for item in items:
                        # Handle 'name as alias' pattern
                        if ' as ' in item:
                            name, alias = [part.strip() for part in item.split(' as ')]
                            imports.append({
                                'name': alias,
                                'path': module,
                                'line': i + 1,
                                'original_name': name
                            })
                        else:
                            imports.append({
                                'name': item,
                                'path': module,
                                'line': i + 1
                            })
                    continue
                
                # ES6 import with namespace import
                match = re.match(r'^\s*import\s+\*\s+as\s+([a-zA-Z0-9_]+)\s+from\s+[\'"]([^\'"]+)[\'"]', line)
                if match:
                    name = match.group(1)
                    module = match.group(2)
                    imports.append({
                        'name': name,
                        'path': module,
                        'line': i + 1,
                        'is_namespace': True
                    })
                    continue
                
                # ES6 import for side effects only
                match = re.match(r'^\s*import\s+[\'"]([^\'"]+)[\'"]', line)
                if match:
                    module = match.group(1)
                    imports.append({
                        'name': module.split('/')[-1],
                        'path': module,
                        'line': i + 1,
                        'is_side_effect': True
                    })
                    continue
                
                # CommonJS require with assignment
                match = re.match(r'^\s*(?:const|var|let)\s+([a-zA-Z0-9_]+)\s+=\s+require\([\'"]([^\'"]+)[\'"]\)', line)
                if match:
                    name = match.group(1)
                    module = match.group(2)
                    imports.append({
                        'name': name,
                        'path': module,
                        'line': i + 1,
                        'is_require': True
                    })
                    continue
                
                # CommonJS require for side effects
                match = re.match(r'^\s*require\([\'"]([^\'"]+)[\'"]\)', line)
                if match:
                    module = match.group(1)
                    imports.append({
                        'name': module.split('/')[-1],
                        'path': module,
                        'line': i + 1,
                        'is_require': True,
                        'is_side_effect': True
                    })
                    continue
        
        elif language == 'java':
            # Handle Java imports
            import_pattern = r'^\s*import\s+(?:static\s+)?([a-zA-Z0-9_.]+(?:\.[*])?);\s*$'
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                match = re.match(import_pattern, line)
                if match:
                    import_path = match.group(1)
                    is_wildcard = import_path.endswith('.*')
                    
                    if is_wildcard:
                        package = import_path[:-2]  # Remove the .*
                        imports.append({
                            'name': f"{package}.*",
                            'path': package,
                            'line': i + 1,
                            'is_wildcard': True
                        })
                    else:
                        # For specific imports, extract the class name
                        parts = import_path.split('.')
                        class_name = parts[-1]
                        package = '.'.join(parts[:-1])
                        
                        imports.append({
                            'name': class_name,
                            'path': import_path,
                            'line': i + 1,
                            'package': package
                        })
        
        elif language == 'csharp':
            # Handle C# using directives
            using_pattern = r'^\s*using\s+(?:static\s+)?([a-zA-Z0-9_.]+)(?:\s+=\s+([a-zA-Z0-9_.]+))?;\s*$'
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                match = re.match(using_pattern, line)
                if match:
                    namespace = match.group(1)
                    target_namespace = match.group(2)
                    
                    if target_namespace:
                        # This is an aliased import: using MyAlias = Company.Product.Module;
                        # In C#, MyAlias is the alias, Company.Product.Module is the actual namespace
                        imports.append({
                            'name': namespace,  # The alias name
                            'path': target_namespace,  # The actual namespace being imported
                            'line': i + 1,
                            'alias': namespace,  # The alias
                            'is_namespace': True
                        })
                    else:
                        # This is a standard import: using System.Collections.Generic;
                        imports.append({
                            'name': namespace.split('.')[-1],
                            'path': namespace,
                            'line': i + 1,
                            'alias': None,
                            'is_namespace': True
                        })
        
        return imports
    
    @staticmethod
    def _extract_function_calls(parsed_data: Dict[str, Any], content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract function calls from parsed data.
        
        Args:
            parsed_data: Parsed file data
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            List of function calls
        """
        # This is a more complex task that would typically require deeper parsing
        # For now, we'll return an empty list as a placeholder
        # In a real implementation, you would use tree-sitter to extract function calls
        return []
    
    @staticmethod
    def _extract_inheritance(parsed_data: Dict[str, Any], content: str, language: str) -> Dict[str, Dict[str, List[str]]]:
        """
        Extract inheritance relationships from parsed data.
        
        Args:
            parsed_data: Parsed file data
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            Dictionary mapping class names to their inheritance information
        """
        inheritance = {}
        
        if language == 'python':
            # Extract Python class inheritance
            import re
            class_pattern = r'class\s+([A-Za-z0-9_]+)\s*\(([^)]*)\):'
            
            matches = re.finditer(class_pattern, content)
            for match in matches:
                class_name = match.group(1)
                parent_classes = [p.strip() for p in match.group(2).split(',') if p.strip()]
                
                inheritance[class_name] = {
                    'superclasses': parent_classes,
                    'interfaces': []  # Python doesn't have formal interfaces
                }
        
        elif language == 'java':
            # Extract Java class inheritance and interface implementation
            import re
            class_pattern = r'class\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?(?:\s+implements\s+([^{]+))?'
            
            matches = re.finditer(class_pattern, content)
            for match in matches:
                class_name = match.group(1)
                superclass = match.group(2)
                interfaces_str = match.group(3)
                
                superclasses = [superclass] if superclass else []
                interfaces = []
                
                if interfaces_str:
                    interfaces = [i.strip() for i in interfaces_str.split(',') if i.strip()]
                
                inheritance[class_name] = {
                    'superclasses': superclasses,
                    'interfaces': interfaces
                }
        
        # Add more language-specific inheritance extraction as needed
        
        return inheritance
    
    @staticmethod
    def _extract_api_endpoints(parsed_data: Dict[str, Any], content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract API endpoints from parsed data.
        
        Args:
            parsed_data: Parsed file data
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            List of API endpoints
        """
        api_endpoints = []
        
        # Look for common API framework patterns
        if language == 'python':
            # Check for Flask routes
            import re
            flask_route_pattern = r'@(?:app|blueprint)\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[([^\]]+)\])?\)'
            
            matches = re.finditer(flask_route_pattern, content)
            for match in matches:
                path = match.group(1)
                methods_str = match.group(2) if match.group(2) else "'GET'"
                methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
                
                # Find the function name (should be right after the decorator)
                function_match = re.search(r'def\s+([A-Za-z0-9_]+)', content[match.end():])
                if function_match:
                    function_name = function_match.group(1)
                    
                    for method in methods:
                        api_endpoints.append({
                            'path': path,
                            'method': method,
                            'function': function_name,
                            'framework': 'Flask'
                        })
        
        # Add more API framework detection as needed
        
        return api_endpoints
    
    @staticmethod
    def _extract_data_models(parsed_data: Dict[str, Any], content: str, language: str) -> List[Dict[str, Any]]:
        """
        Extract data models from parsed data.
        
        Args:
            parsed_data: Parsed file data
            content: Content of the file
            language: Programming language of the file
            
        Returns:
            List of data models
        """
        data_models = []
        
        if language == 'python':
            # Look for SQLAlchemy models
            classes = parsed_data.get('classes', [])
            
            for cls in classes:
                # Check if this is a SQLAlchemy model
                class_content = cls.get('content', '')
                
                # Check for common SQLAlchemy patterns
                is_sqlalchemy_model = (
                    '__tablename__' in class_content or 
                    'Column(' in class_content or 
                    'relationship(' in class_content or
                    'ForeignKey(' in class_content or
                    'Base' in cls.get('superclasses', [])
                )
                
                if is_sqlalchemy_model:
                    # Extract fields from the class content
                    fields = []
                    import re
                    
                    # Extract table name
                    table_name_match = re.search(r'__tablename__\s*=\s*[\'"]([^\'"]+)[\'"]', class_content)
                    table_name = table_name_match.group(1) if table_name_match else None
                    
                    # Extract columns
                    column_pattern = r'(\w+)\s*=\s*Column\(([^)]+)\)'
                    column_matches = re.finditer(column_pattern, class_content)
                    
                    for match in column_matches:
                        column_name = match.group(1)
                        column_def = match.group(2)
                        
                        # Determine field type
                        field_type = "Unknown"
                        if "Integer" in column_def:
                            field_type = "Integer"
                        elif "String" in column_def:
                            field_type = "String"
                        elif "Boolean" in column_def:
                            field_type = "Boolean"
                        elif "DateTime" in column_def:
                            field_type = "DateTime"
                        elif "Float" in column_def:
                            field_type = "Float"
                        
                        # Determine constraints
                        constraints = []
                        if "primary_key=True" in column_def:
                            constraints.append("PRIMARY KEY")
                        if "unique=True" in column_def:
                            constraints.append("UNIQUE")
                        if "nullable=False" in column_def:
                            constraints.append("NOT NULL")
                        if "ForeignKey" in column_def:
                            fk_match = re.search(r'ForeignKey\([\'"]([^\'"]+)[\'"]\)', column_def)
                            if fk_match:
                                constraints.append(f"FOREIGN KEY ({fk_match.group(1)})")
                        
                        fields.append({
                            'name': column_name,
                            'type': field_type,
                            'constraints': constraints
                        })
                    
                    # Extract relationships
                    relationship_pattern = r'(\w+)\s*=\s*relationship\(([^)]+)\)'
                    relationship_matches = re.finditer(relationship_pattern, class_content)
                    
                    for match in relationship_matches:
                        rel_name = match.group(1)
                        rel_def = match.group(2)
                        
                        # Extract target entity
                        target_match = re.search(r'[\'"]([^\'"]+)[\'"]', rel_def)
                        target = target_match.group(1) if target_match else "Unknown"
                        
                        fields.append({
                            'name': rel_name,
                            'type': f"Relationship<{target}>",
                            'constraints': []
                        })
                    
                    # Create the data model
                    data_models.append({
                        'name': cls.get('name', ''),
                        'table_name': table_name,
                        'fields': fields
                    })
        
        # Add more language-specific data model extraction as needed
        
        return data_models 