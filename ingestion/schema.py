"""
Enhanced Schema for Ingestion System

This module integrates and extends the knowledge_graph schema classes
to provide a rich domain model for the ingestion pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Union, Any

# Base classes for nodes and relationships
@dataclass
class Node:
    """Base class for all nodes in the knowledge graph."""
    id: str
    name: str
    type: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    embedding: Optional[List[float]] = None
    properties: Dict[str, Union[str, int, float, bool, List]] = field(default_factory=dict)


@dataclass
class Relationship:
    """Base class for all relationships in the knowledge graph."""
    source_id: str
    target_id: str
    type: str
    weight: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    properties: Dict[str, Union[str, int, float, bool, List]] = field(default_factory=dict)


# Core entity types
@dataclass
class Repository(Node):
    """Represents a code repository."""
    id: str
    name: str
    url: str = ""
    vcs_type: str = "git"  # git, svn, etc.
    description: str = ""
    default_branch: str = "main"
    last_commit_hash: str = ""
    last_indexed_at: Optional[datetime] = None
    type: str = "Repository"


@dataclass
class File(Node):
    """Represents a file in a repository."""
    id: str
    name: str
    path: str = ""
    size: int = 0
    language: str = ""
    content_hash: str = ""
    last_modified_at: Optional[datetime] = None
    is_documentation: bool = False
    type: str = "File"


@dataclass
class Function(Node):
    """Represents a function or method in code."""
    id: str
    name: str
    signature: str = ""
    return_type: str = ""
    parameters: List[Dict[str, str]] = field(default_factory=list)
    complexity: Optional[float] = None
    line_count: int = 0
    docstring: str = ""
    start_line: int = 0
    end_line: int = 0
    unique_id: str = ""
    type: str = "Function"


@dataclass
class Class(Node):
    """Represents a class in code."""
    id: str
    name: str
    superclasses: List[str] = field(default_factory=list)
    interfaces: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[Dict[str, str]] = field(default_factory=list)
    docstring: str = ""
    start_line: int = 0
    end_line: int = 0
    unique_id: str = ""
    type: str = "Class"


@dataclass
class Service(Node):
    """Represents a deployed service."""
    id: str
    name: str
    environment: str = "production"  # production, staging, development
    endpoints: List[str] = field(default_factory=list)
    version: str = ""
    status: str = "active"  # active, deprecated, planned
    health: str = "healthy"  # healthy, degraded, down
    repository_url: str = ""
    description: str = ""
    type: str = "Service"


@dataclass
class CodeChunk(Node):
    """Represents a chunk of code with embedding."""
    id: str
    name: str
    content: str = ""
    start_line: int = 0
    end_line: int = 0
    parent_id: str = ""
    parent_type: str = ""  # File, Function, Class
    chunk_id: str = ""
    repo_url: str = ""
    service_name: str = ""
    is_documentation: bool = False
    type: str = "CodeChunk"


@dataclass
class ApiEndpoint(Node):
    """Represents an API endpoint."""
    id: str
    name: str
    path: str = ""
    method: str = ""  # GET, POST, etc.
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: str = ""
    description: str = ""
    service_name: str = ""
    repo_url: str = ""
    type: str = "ApiEndpoint"


@dataclass
class DataModel(Node):
    """Represents a data model or schema."""
    id: str
    name: str
    fields: List[Dict[str, str]] = field(default_factory=list)
    description: str = ""
    service_name: str = ""
    repo_url: str = ""
    type: str = "DataModel"


@dataclass
class Dependency(Node):
    """Represents an external library or service dependency."""
    id: str
    name: str
    version: str = ""
    license: str = ""
    source: str = ""  # npm, pypi, maven, etc.
    is_direct: bool = True
    service_name: str = ""
    repo_url: str = ""
    type: str = "Dependency"


# Define relationship types
RELATIONSHIP_TYPES = {
    "BELONGS_TO": "Membership relationship",
    "CONTAINS": "Parent-child relationship",
    "DEPENDS_ON": "Dependency relationship",
    "CALLS": "Function call relationship",
    "IMPORTS": "Import relationship",
    "COMMUNICATES_WITH": "Service-to-service communication",
    "EXPOSES": "API exposure relationship",
    "IMPLEMENTS": "Implementation relationship",
    "INHERITS_FROM": "Inheritance relationship",
    "USES": "Usage relationship",
    "REFERENCES": "Cross-reference relationship"
}


# Schema version
SCHEMA_VERSION = "1.0.0"


def get_node_types() -> Set[str]:
    """Return all valid node types in the schema."""
    return {
        "Repository",
        "File",
        "Function",
        "Class",
        "Service",
        "CodeChunk",
        "ApiEndpoint",
        "DataModel",
        "Dependency"
    }


def get_relationship_types() -> Set[str]:
    """Return all valid relationship types in the schema."""
    return set(RELATIONSHIP_TYPES.keys()) 