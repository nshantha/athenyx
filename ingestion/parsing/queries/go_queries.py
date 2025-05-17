"""
Tree-sitter query patterns for Go.
Contains optimized patterns for detecting functions, structs, and other code structures.
"""

# Go function patterns for tree-sitter
GO_FUNCTION_QUERY = """
(function_declaration
  name: (identifier) @name) @function
"""

# Go method patterns for tree-sitter
GO_METHOD_QUERY = """
(method_declaration
  name: (field_identifier) @name) @function
"""

# Go struct patterns for tree-sitter
GO_STRUCT_QUERY = """
(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (struct_type))) @struct
"""

# Go interface patterns for tree-sitter
GO_INTERFACE_QUERY = """
(type_declaration
  (type_spec
    name: (type_identifier) @name
    type: (interface_type))) @interface
"""

# Go variable patterns for tree-sitter
GO_VARIABLE_QUERY = """
(var_declaration
  (var_spec
    name: (identifier) @name)) @variable
"""

# Dictionary to easily access all queries
GO_QUERIES = {
    "functions": GO_FUNCTION_QUERY,
    "methods": GO_METHOD_QUERY,
    "structs": GO_STRUCT_QUERY,
    "interfaces": GO_INTERFACE_QUERY,
    "variables": GO_VARIABLE_QUERY
} 