"""
Tree-sitter query patterns for Java.
Contains optimized patterns for detecting methods, classes, and other code structures.
"""

# Java method patterns for tree-sitter
JAVA_METHOD_QUERY = """
(method_declaration
  name: (identifier) @name) @function
"""

# Java class patterns for tree-sitter
JAVA_CLASS_QUERY = """
(class_declaration
  name: (identifier) @name) @class
"""

# Java interface patterns for tree-sitter
JAVA_INTERFACE_QUERY = """
(interface_declaration
  name: (identifier) @name) @interface
"""

# Java enum patterns for tree-sitter
JAVA_ENUM_QUERY = """
(enum_declaration
  name: (identifier) @name) @enum
"""

# Java variable patterns for tree-sitter
JAVA_VARIABLE_QUERY = """
(field_declaration
  declarator: (variable_declarator
    name: (identifier) @name)) @variable
"""

# Dictionary to easily access all queries
JAVA_QUERIES = {
    "functions": JAVA_METHOD_QUERY,
    "classes": JAVA_CLASS_QUERY,
    "interfaces": JAVA_INTERFACE_QUERY,
    "enums": JAVA_ENUM_QUERY,
    "variables": JAVA_VARIABLE_QUERY
} 