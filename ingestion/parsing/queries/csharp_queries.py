"""
Tree-sitter query patterns for C#.
Contains optimized patterns for detecting methods, classes, and other code structures.
"""

# C# method patterns for tree-sitter
CSHARP_METHOD_QUERY = """
(method_declaration
  name: (identifier) @name) @function
"""

# C# class patterns for tree-sitter
CSHARP_CLASS_QUERY = """
(class_declaration
  name: (identifier) @name) @class
"""

# C# interface patterns for tree-sitter
CSHARP_INTERFACE_QUERY = """
(interface_declaration
  name: (identifier) @name) @interface
"""

# C# struct patterns for tree-sitter
CSHARP_STRUCT_QUERY = """
(struct_declaration
  name: (identifier) @name) @struct
"""

# C# enum patterns for tree-sitter
CSHARP_ENUM_QUERY = """
(enum_declaration
  name: (identifier) @name) @enum
"""

# C# variable patterns for tree-sitter
CSHARP_VARIABLE_QUERY = """
(field_declaration
  (variable_declaration
    (variable_declarator
      name: (identifier) @name))) @variable
"""

# Dictionary to easily access all queries
CSHARP_QUERIES = {
    "functions": CSHARP_METHOD_QUERY,
    "classes": CSHARP_CLASS_QUERY,
    "interfaces": CSHARP_INTERFACE_QUERY,
    "structs": CSHARP_STRUCT_QUERY,
    "enums": CSHARP_ENUM_QUERY,
    "variables": CSHARP_VARIABLE_QUERY
} 