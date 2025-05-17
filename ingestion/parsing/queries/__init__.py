"""
Query modules for tree-sitter parsing.
This package contains language-specific query patterns for extracting
structure from source code using tree-sitter.
"""

from ingestion.parsing.queries.python_queries import PYTHON_QUERIES
from ingestion.parsing.queries.javascript_queries import JAVASCRIPT_QUERIES
from ingestion.parsing.queries.java_queries import JAVA_QUERIES
from ingestion.parsing.queries.csharp_queries import CSHARP_QUERIES
from ingestion.parsing.queries.go_queries import GO_QUERIES

# Dictionary mapping language names to their query collections
LANGUAGE_QUERIES = {
    'python': PYTHON_QUERIES,
    'javascript': JAVASCRIPT_QUERIES,
    'java': JAVA_QUERIES,
    'csharp': CSHARP_QUERIES,
    'go': GO_QUERIES
}

def get_queries_for_language(language: str) -> dict:
    """
    Get the query collection for a specific language.
    
    Args:
        language: The programming language to get queries for
        
    Returns:
        A dictionary containing query strings for the language,
        or None if the language is not supported
    """
    return LANGUAGE_QUERIES.get(language.lower()) 