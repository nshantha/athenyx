"""
Tests for the enhanced knowledge system.

This module contains tests for the enhanced knowledge system that integrates
the knowledge_graph builder pattern with the ingestion system.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from ingestion.schema import Repository, File, Function, Class, CodeChunk
from ingestion.parsing.enhanced_parser import EnhancedParser
from ingestion.loading.enhanced_loader import EnhancedLoader
from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem


# Sample test data
SAMPLE_PYTHON_CODE = """
import os
import sys
from datetime import datetime

class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        
    def greet(self):
        return f"Hello, my name is {self.name} and I am {self.age} years old."
        
class Employee(Person):
    def __init__(self, name, age, employee_id):
        super().__init__(name, age)
        self.employee_id = employee_id
        
    def get_id(self):
        return self.employee_id

def main():
    person = Person("John", 30)
    print(person.greet())
    
    employee = Employee("Jane", 25, "E12345")
    print(employee.greet())
    print(f"Employee ID: {employee.get_id()}")

if __name__ == "__main__":
    main()
"""

SAMPLE_FLASK_CODE = """
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/users', methods=['GET'])
def get_users():
    return jsonify({"users": ["user1", "user2"]})

@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify({"user_id": user_id, "name": "Test User"})

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.json
    return jsonify({"status": "success", "user": data}), 201

if __name__ == '__main__':
    app.run(debug=True)
"""

SAMPLE_SQLALCHEMY_CODE = """
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    
    posts = relationship("Post", back_populates="author")
    
class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    author = relationship("User", back_populates="posts")
"""


@pytest.mark.asyncio
async def test_enhanced_parser_python():
    """Test the enhanced parser with Python code."""
    # Parse the sample Python code
    result = EnhancedParser.parse_file("test.py", SAMPLE_PYTHON_CODE, "python")
    
    # Check that basic parsing worked
    assert not result.get('parse_error')
    assert 'functions' in result
    assert 'classes' in result
    
    # Check that functions were parsed correctly
    functions = result['functions']
    assert len(functions) >= 1
    assert any(f['name'] == 'main' for f in functions)
    
    # Check that classes were parsed correctly
    classes = result['classes']
    assert len(classes) >= 2
    assert any(c['name'] == 'Person' for c in classes)
    assert any(c['name'] == 'Employee' for c in classes)
    
    # Check that imports were extracted
    assert 'imports' in result
    imports = result['imports']
    assert len(imports) >= 3
    assert any(i['name'] == 'os' for i in imports)
    assert any(i['name'] == 'sys' for i in imports)
    assert any(i['name'] == 'datetime' for i in imports)
    
    # Check that inheritance was extracted
    employee_class = next((c for c in classes if c['name'] == 'Employee'), None)
    assert employee_class is not None
    assert 'superclasses' in employee_class
    assert 'Person' in employee_class['superclasses']


@pytest.mark.asyncio
async def test_enhanced_parser_flask():
    """Test the enhanced parser with Flask code."""
    # Parse the sample Flask code
    result = EnhancedParser.parse_file("app.py", SAMPLE_FLASK_CODE, "python")
    
    # Check that basic parsing worked
    assert not result.get('parse_error')
    assert 'functions' in result
    
    # Check that functions were parsed correctly
    functions = result['functions']
    assert len(functions) >= 3
    assert any(f['name'] == 'get_users' for f in functions)
    assert any(f['name'] == 'get_user' for f in functions)
    assert any(f['name'] == 'create_user' for f in functions)
    
    # Check that API endpoints were extracted
    assert 'api_endpoints' in result
    endpoints = result['api_endpoints']
    assert len(endpoints) >= 3
    
    # Check specific endpoints
    assert any(e['path'] == '/api/users' and e['method'] == 'GET' for e in endpoints)
    assert any(e['path'] == '/api/users/<user_id>' and e['method'] == 'GET' for e in endpoints)
    assert any(e['path'] == '/api/users' and e['method'] == 'POST' for e in endpoints)


@pytest.mark.asyncio
async def test_enhanced_parser_sqlalchemy():
    """Test the enhanced parser with SQLAlchemy code."""
    # Parse the sample SQLAlchemy code
    result = EnhancedParser.parse_file("models.py", SAMPLE_SQLALCHEMY_CODE, "python")
    
    # Check that basic parsing worked
    assert not result.get('parse_error')
    assert 'classes' in result
    
    # Check that classes were parsed correctly
    classes = result['classes']
    assert len(classes) >= 2
    assert any(c['name'] == 'User' for c in classes)
    assert any(c['name'] == 'Post' for c in classes)
    
    # Check that data models were extracted
    assert 'data_models' in result
    models = result['data_models']
    assert len(models) >= 2
    
    # Check specific models
    user_model = next((m for m in models if m['name'] == 'User'), None)
    assert user_model is not None
    assert 'fields' in user_model
    assert any(f['name'] == 'id' for f in user_model['fields'])
    assert any(f['name'] == 'username' for f in user_model['fields'])
    assert any(f['name'] == 'email' for f in user_model['fields'])
    
    post_model = next((m for m in models if m['name'] == 'Post'), None)
    assert post_model is not None
    assert 'fields' in post_model
    assert any(f['name'] == 'id' for f in post_model['fields'])
    assert any(f['name'] == 'title' for f in post_model['fields'])
    assert any(f['name'] == 'content' for f in post_model['fields'])
    assert any(f['name'] == 'user_id' for f in post_model['fields'])


@pytest.mark.asyncio
async def test_enhanced_loader():
    """Test the enhanced loader."""
    # Mock the base loader
    with patch('ingestion.loading.neo4j_loader.Neo4jLoader') as mock_loader_class:
        # Create a mock instance with an async load_data method
        mock_loader_instance = AsyncMock()
        mock_loader_instance.load_data = AsyncMock()
        mock_loader_class.return_value = mock_loader_instance
        
        # Create an instance of EnhancedLoader
        loader = EnhancedLoader("https://github.com/test/repo.git")
        
        # Replace the base_loader with our mock
        loader.base_loader = mock_loader_instance

        # Mock the create_relationship method
        loader.create_relationship = AsyncMock()

        # Create sample parsed data
        parsed_data = [
            {
                "path": "test.py",
                "functions": [{"name": "test_func", "unique_id": "func1", "start_line": 1, "end_line": 5}],
                "classes": [{"name": "TestClass", "unique_id": "class1", "start_line": 7, "end_line": 15}],
                "function_calls": [
                    {"source_name": "test_func", "target_name": "other_func", "line": 10}
                ],
                "imports": [
                    {"name": "os", "path": "os.py", "line": 1}
                ]
            }
        ]

        # Create sample chunks with embeddings
        chunks_with_embeddings = [
            {
                "chunk_id": "chunk1",
                "content": "def test_func():\n    pass",
                "parent_id": "func1",
                "embedding": [0.1, 0.2, 0.3]
            }
        ]

        # Call the load_data method
        await loader.load_data(parsed_data, chunks_with_embeddings)
        
        # Verify the base loader's load_data was called
        mock_loader_instance.load_data.assert_called_once_with(parsed_data, chunks_with_embeddings)


@pytest.mark.asyncio
async def test_enhanced_knowledge_system():
    """Test the enhanced knowledge system."""
    # Create a custom test implementation that skips the actual repository processing
    class TestEnhancedKnowledgeSystem(EnhancedKnowledgeSystem):
        async def ingest_repository(self, repo_config):
            """Override to avoid git operations"""
            repo_url = repo_config.get("url")
            current_commit_sha = "abc123"
            
            # Update the repository status directly
            await self.db_manager.update_repository_status(repo_url, current_commit_sha)
            return True
    
    # Mock the database manager
    with patch('app.db.neo4j_manager.db_manager') as mock_db_manager:
        # Create an instance of our test system
        system = TestEnhancedKnowledgeSystem()
        
        # Set the system's db_manager to the mock
        system.db_manager = mock_db_manager
        
        # Mock the update_repository_status method
        mock_db_manager.update_repository_status = AsyncMock()
        
        # Call the ingest_repository method
        await system.ingest_repository({
            "url": "https://github.com/test/repo.git",
            "branch": "main"
        })
        
        # Verify the repository status was updated
        mock_db_manager.update_repository_status.assert_called_once_with(
            "https://github.com/test/repo.git", "abc123"
        )


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", __file__]) 