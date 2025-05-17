"""
Tree-sitter query patterns for JavaScript.
Contains optimized patterns for detecting functions, classes, and other code structures.
"""

# JavaScript function patterns for tree-sitter
JAVASCRIPT_FUNCTION_QUERY = """
(function_declaration 
  name: (identifier) @name) @function
"""

# JavaScript class patterns for tree-sitter
JAVASCRIPT_CLASS_QUERY = """
(class_declaration
  name: (identifier) @name) @class
"""

# JavaScript method patterns for tree-sitter
JAVASCRIPT_METHOD_QUERY = """
(method_definition
  name: (property_identifier) @name) @method
"""

# JavaScript variable patterns
JAVASCRIPT_VARIABLE_QUERY = """
(variable_declarator
  name: (identifier) @name) @variable
"""

# Dictionary to easily access all queries
JAVASCRIPT_QUERIES = {
    "functions": JAVASCRIPT_FUNCTION_QUERY,
    "classes": JAVASCRIPT_CLASS_QUERY,
    "methods": JAVASCRIPT_METHOD_QUERY,
    "variables": JAVASCRIPT_VARIABLE_QUERY
} 