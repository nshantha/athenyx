"""
Module for accessing Tree-sitter queries for different languages.
This module provides a unified interface to get query patterns for all supported languages.
"""
import logging
from typing import Dict, Optional

# Import language-specific query files
from ingestion.parsing.queries.python_queries import PYTHON_QUERIES
from ingestion.parsing.queries.javascript_queries import JAVASCRIPT_QUERIES
from ingestion.parsing.queries.java_queries import JAVA_QUERIES
from ingestion.parsing.queries.csharp_queries import CSHARP_QUERIES
from ingestion.parsing.queries.go_queries import GO_QUERIES

logger = logging.getLogger(__name__)

# Map of language names to query dictionaries
LANGUAGE_QUERIES = {
    'python': PYTHON_QUERIES,
    'javascript': JAVASCRIPT_QUERIES,
    'typescript': JAVASCRIPT_QUERIES,  # Use JS queries for TypeScript
    'java': JAVA_QUERIES,
    'csharp': CSHARP_QUERIES,
    'go': GO_QUERIES
}

def get_queries_for_language(language: str) -> Optional[Dict[str, str]]:
    """
    Get the Tree-sitter query patterns for a specific language.
    
    Args:
        language: The programming language name (lowercase)
        
    Returns:
        Dictionary of entity types and their query patterns, or None if language not supported
    """
    if language not in LANGUAGE_QUERIES:
        logger.warning(f"No queries available for language: {language}")
        return None
        
    return LANGUAGE_QUERIES[language] 