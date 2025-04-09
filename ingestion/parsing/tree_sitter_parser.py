# ingestion/parsing/tree_sitter_parser.py
import logging
import os # Ensure os is imported if needed later, though not directly here
from tree_sitter import Language, Parser, Node
from tree_sitter_languages import get_language, get_parser # Helper library
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Pre-load parsers to avoid reloading on each call
PARSERS = {}
LANGUAGES = {}

def _initialize_parser(language_name: str):
    """Initializes and caches the parser for a given language."""
    if language_name not in PARSERS:
        try:
            # Ensure correct grammar names are used (these are common)
            grammar_name = language_name
            if language_name == 'csharp': # tree-sitter-languages might use 'c_sharp' or 'csharp'
                 grammar_name = 'c_sharp' # Adjust if needed based on tree-sitter-languages output/docs
            elif language_name == 'javascript':
                 grammar_name = 'javascript' # Could also be 'typescript' for broader compatibility if grammar covers JS

            lang: Language = get_language(grammar_name)
            parser: Parser = get_parser(grammar_name)
            LANGUAGES[language_name] = lang # Store by the name we'll use internally
            PARSERS[language_name] = parser
            logger.info(f"Initialized tree-sitter parser for language: {language_name} (using grammar '{grammar_name}')")
        except Exception as e:
            logger.error(f"Failed to initialize tree-sitter parser for '{language_name}'. Is the grammar installed? Error: {e}", exc_info=True)
            # Raise error to prevent proceeding without parser
            raise RuntimeError(f"Tree-sitter parser for {language_name} not available.") from e

# Initialize parsers for all supported languages
_initialize_parser('python')
_initialize_parser('go')
_initialize_parser('csharp') # Use 'csharp' internally
_initialize_parser('java')
_initialize_parser('javascript') # Use 'javascript' internally


class TreeSitterParser:

    @staticmethod
    def get_node_text(node: Node, content_bytes: bytes) -> str:
        """Safely extracts text from a node."""
        return content_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='replace')

    @staticmethod
    def _get_identifier(node: Node, content_bytes: bytes) -> Optional[str]:
        """Finds the first 'identifier' node or common name field."""
        # Check common field names first
        name_node = node.child_by_field_name('name')
        if name_node and name_node.type == 'identifier':
            return TreeSitterParser.get_node_text(name_node, content_bytes)

        # Check for declarator field (common in C-like languages)
        declarator_node = node.child_by_field_name('declarator')
        if declarator_node and declarator_node.type == 'identifier':
             return TreeSitterParser.get_node_text(declarator_node, content_bytes)

        # Fallback: search direct children for identifier
        for child in node.children:
            if child.type == 'identifier':
                # Avoid picking up type identifiers if possible, crude check
                # if child.prev_named_sibling and child.prev_named_sibling.type.endswith('type'):
                #    continue
                return TreeSitterParser.get_node_text(child, content_bytes)
        return None # Could not find identifier

    @staticmethod
    def _generic_parse(language_name: str, file_path: str, content: str, structure_queries: Dict[str, str]) -> Dict[str, Any]:
        """Generic parsing logic using tree-sitter queries."""
        parser = PARSERS.get(language_name)
        lang = LANGUAGES.get(language_name)
        if not parser or not lang:
            logger.error(f"{language_name.capitalize()} parser not initialized.")
            return {"path": file_path, "functions": [], "classes": [], "structs": [], "interfaces": [], "parse_error": True}

        content_bytes = bytes(content, "utf8")
        try:
            tree = parser.parse(content_bytes)
            root_node = tree.root_node
        except Exception as e:
            logger.warning(f"Tree-sitter failed to parse file {file_path} ({language_name}): {e}")
            return {"path": file_path, "functions": [], "classes": [], "structs": [], "interfaces": [], "parse_error": True}

        results: Dict[str, List[Dict[str, Any]]] = {k: [] for k in structure_queries.keys()}

        for structure_type, query_string in structure_queries.items():
            try:
                query = lang.query(query_string)
                captures = query.captures(root_node)
            except Exception as e:
                 logger.error(f"Failed to compile or run query for {language_name} {structure_type}: {e}")
                 continue # Skip this structure type if query fails

            # Use a dictionary to store items by node ID to handle multiple captures per node if query is complex
            items_by_node_id = {}
            for node, capture_name in captures:
                 if node.id not in items_by_node_id:
                      start_line = node.start_point[0] + 1
                      end_line = node.end_point[0] + 1
                      node_text = TreeSitterParser.get_node_text(node, content_bytes)
                      name = TreeSitterParser._get_identifier(node, content_bytes)

                      if name: # Only add if we found a name
                        # Simple unique ID - consider adding class/struct context if nested
                        unique_id = f"{file_path}::{name}" # May need refinement for overloaded methods etc.
                        items_by_node_id[node.id] = {
                              "name": name,
                              "unique_id": unique_id,
                              "start_line": start_line,
                              "end_line": end_line,
                              "content": node_text # Full text of the captured node
                          }

            results[structure_type].extend(items_by_node_id.values())

        logger.debug(f"Parsed {file_path} ({language_name}): Found " +
                     ", ".join(f"{len(v)} {k}" for k, v in results.items()))

        # Flatten results into the expected format (functions, classes, etc.)
        output = {"path": file_path, "parse_error": False}
        output.update(results)
        return output


    # --- Language Specific Parsing Methods ---

    @staticmethod
    def parse_python(file_path: str, content: str) -> Dict[str, Any]:
        # Basic queries for Python functions and classes
        queries = {
            "functions": "(function_definition name: (identifier) @name) @function",
            "classes": "(class_definition name: (identifier) @name) @class"
        }
        return TreeSitterParser._generic_parse('python', file_path, content, queries)

    @staticmethod
    def parse_go(file_path: str, content: str) -> Dict[str, Any]:
         # Basic queries for Go functions, methods, types (structs)
         # Note: Go methods are functions with receivers, harder to distinguish simply
         queries = {
             "functions": """
                 [
                     (function_declaration name: (identifier) @name) @function
                     (method_declaration name: (field_identifier) @name) @function
                 ]
             """,
             "structs": "(type_declaration (type_spec name: (type_identifier) @name (struct_type) ) ) @struct"
             # Interfaces could be added: (type_declaration (type_spec name: (type_identifier) @name (interface_type)))
         }
         # Store structs under 'classes' key for simplicity or adjust loader
         result = TreeSitterParser._generic_parse('go', file_path, content, queries)
         result["classes"] = result.pop("structs", []) # Rename 'structs' to 'classes'
         return result

    @staticmethod
    def parse_csharp(file_path: str, content: str) -> Dict[str, Any]:
         # Basic queries for C# methods, classes, interfaces, structs
         queries = {
             "functions": "(method_declaration name: (identifier) @name) @function",
             "classes": "(class_declaration name: (identifier) @name) @class",
             "interfaces": "(interface_declaration name: (identifier) @name) @interface",
             "structs": "(struct_declaration name: (identifier) @name) @struct"
         }
         # Combine structs and interfaces into 'classes' for simplicity or adjust loader
         result = TreeSitterParser._generic_parse('csharp', file_path, content, queries)
         result["classes"].extend(result.pop("interfaces", []))
         result["classes"].extend(result.pop("structs", []))
         return result

    @staticmethod
    def parse_java(file_path: str, content: str) -> Dict[str, Any]:
         # Basic queries for Java methods, classes, interfaces
         queries = {
             "functions": "(method_declaration name: (identifier) @name) @function",
             "classes": "(class_declaration name: (identifier) @name) @class",
             "interfaces": "(interface_declaration name: (identifier) @name) @interface"
         }
          # Combine interfaces into 'classes' for simplicity or adjust loader
         result = TreeSitterParser._generic_parse('java', file_path, content, queries)
         result["classes"].extend(result.pop("interfaces", []))
         return result

    @staticmethod
    def parse_javascript(file_path: str, content: str) -> Dict[str, Any]:
         # Basic queries for JS functions (incl. arrows) and classes
         queries = {
             "functions": """
                 [
                     (function_declaration name: (identifier) @name) @function
                     (method_definition name: (property_identifier) @name) @function
                     (variable_declarator
                         name: (identifier) @name
                         value: [(arrow_function) (function)]) @function
                      (pair
                         key: (property_identifier) @name
                         value: [(arrow_function) (function)]) @function


                 ]
             """,
              "classes": "(class_declaration name: (identifier) @name) @class"
         }
         return TreeSitterParser._generic_parse('javascript', file_path, content, queries)


    # --- Main Dispatch Method ---

    @staticmethod
    def parse_file(file_path: str, content: str, language: str) -> Optional[Dict[str, Any]]:
        """Parses a file based on the detected or specified language."""
        language_lower = language.lower()
        if language_lower == 'python':
            return TreeSitterParser.parse_python(file_path, content)
        elif language_lower == 'go':
             return TreeSitterParser.parse_go(file_path, content)
        elif language_lower == 'csharp' or language_lower == 'c#': # Allow both variations
             return TreeSitterParser.parse_csharp(file_path, content)
        elif language_lower == 'java':
             return TreeSitterParser.parse_java(file_path, content)
        elif language_lower == 'javascript' or language_lower == 'js' or language_lower == 'node': # Allow variations
             return TreeSitterParser.parse_javascript(file_path, content)
        else:
            logger.warning(f"Unsupported language '{language}' for parsing file {file_path}. Skipping structural parsing.")
            # Return basic file info but mark as unparsed structurally?
            # Or return None to indicate no structural data extracted. Let's return None.
            return None