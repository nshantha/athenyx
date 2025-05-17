"""
Athenyx ingestion package for code analysis and knowledge graph generation.
"""

# Expose key modules
from ingestion.sources import git_loader
from ingestion.parsing import tree_sitter_parser, queries
from ingestion.processing import chunking, embedding
from ingestion.loading import neo4j_loader
from ingestion.modules import knowledge_system, microservices, api
