"""
Tree-sitter query patterns for Python.
Contains optimized patterns for detecting functions, classes, and other code structures.
"""

# Python function patterns for tree-sitter
PYTHON_FUNCTION_QUERY = """
(function_definition
  name: (identifier) @name) @function
"""

# Python class patterns for tree-sitter
PYTHON_CLASS_QUERY = """
(class_definition
  name: (identifier) @name) @class
"""

# Python interface patterns (for protocol/abstract classes)
PYTHON_INTERFACE_QUERY = """
(class_definition
  name: (identifier) @name
  superclasses: (argument_list)) @class
"""

# Variable patterns
PYTHON_VARIABLE_QUERY = """
(assignment 
  left: (identifier) @name) @variable
"""

# Dictionary to easily access all queries
PYTHON_QUERIES = {
    "functions": PYTHON_FUNCTION_QUERY,
    "classes": PYTHON_CLASS_QUERY,
    "interfaces": PYTHON_INTERFACE_QUERY,
    "variables": PYTHON_VARIABLE_QUERY
} 