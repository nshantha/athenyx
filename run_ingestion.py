#!/usr/bin/env python
"""
Unified ingestion script that combines all steps:
1. Clear repo data (optional)
2. Run main ingestion
3. Fix relationships
4. Fix ontology structure (ensure Classes and Functions are connected to CodeChunks)
"""
import asyncio
import os
import sys
import logging
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Add the project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

async def test_neo4j_connection() -> bool:
    """Test connection to Neo4j database"""
    try:
        from app.db.neo4j_manager import db_manager
        
        await db_manager.connect()
        logger.info("Successfully connected to Neo4j")
        await db_manager.close()
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return False

async def clear_repository_data(repo_url: str) -> bool:
    """
    Clear existing data for a repository
    
    Args:
        repo_url: Repository URL to clear
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from app.db.neo4j_manager import db_manager
        
        logger.info(f"Clearing data for repository: {repo_url}")
        
        # Connect to Neo4j database
        await db_manager.connect()
        
        # Delete all nodes and relationships related to this repository
        await db_manager.run_query(
            """
            MATCH (n)
            WHERE n.repo_url = $repo_url OR n.url = $repo_url
            DETACH DELETE n
            """,
            {"repo_url": repo_url}
        )
        
        logger.info(f"Successfully cleared data for repository: {repo_url}")
        await db_manager.close()
        return True
    except Exception as e:
        logger.error(f"Failed to clear repository data: {e}")
        return False

async def run_ingestion(repo_url: str, description: Optional[str] = None, 
                       clear: bool = False, force_reindex: bool = False) -> bool:
    """
    Run the main ingestion process
    
    Args:
        repo_url: URL of the repository to ingest
        description: Optional description of the repository
        clear: Whether to clear existing repository data before ingestion
        force_reindex: Whether to force reindexing of the repository even if it exists
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Clear repository data if requested
        if clear:
            if not await clear_repository_data(repo_url):
                return False
        
        # Verify Neo4j connection
        if not await test_neo4j_connection():
            logger.error("Failed to connect to Neo4j. Please check your credentials and try again.")
            return False
            
        from ingestion.config import ingestion_settings
        from ingestion.modules.enhanced_knowledge_system import EnhancedKnowledgeSystem
        from helpers.fix_relationships import fix_relationships
        from helpers.fix_class_connections import fix_class_connections
        from helpers.fix_function_connections import fix_function_connections
        
        # Create an instance of the enhanced knowledge system
        knowledge_system = EnhancedKnowledgeSystem()
        
        # Check if the repository has already been indexed
        from app.db.neo4j_manager import db_manager
        existing_commit = await db_manager.get_repository_status(repo_url)
        logger.info(f"Repository status: {'Already indexed' if existing_commit else 'Not indexed'}")
            
        # Only proceed with ingestion if no data exists for this repo or force reindex is set
        if force_reindex or not existing_commit:
            # Perform the main ingestion
            logger.info("Starting main ingestion process")
            try:
                await knowledge_system.ingest_repository({
                    "url": repo_url,
                    "description": description or f"Repository {repo_url}"
                })
            except Exception as e:
                logger.error(f"An error occurred during ingestion: {e}")
                return False
            
            # Fix relationships
            logger.info("Fixing relationships between nodes")
            try:
                await fix_relationships(repo_url)
            except Exception as e:
                logger.error(f"An error occurred while fixing relationships: {e}")
                # Continue execution even if relationship fixing fails
            
            # Fix ontology structure (Class and Function connections)
            logger.info("Fixing ontology structure (connecting Classes and Functions)")
            try:
                await fix_class_connections(repo_url)
                await fix_function_connections(repo_url)
            except Exception as e:
                logger.error(f"An error occurred while fixing ontology structure: {e}")
                # Continue execution even if ontology fixing fails
            
            logger.info("Ingestion completed successfully")
        else:
            logger.info(f"Repository already indexed with commit hash: {existing_commit}")
            logger.info("Use --force-reindex to reindex anyway")
        
        return True
    except Exception as e:
        logger.error(f"An error occurred during ingestion: {e}")
        return False

def get_neo4j_credentials() -> dict:
    """
    Get Neo4j credentials from environment variables or prompt the user.
    
    Returns:
        Dictionary with Neo4j credentials
    """
    credentials = {
        "uri": os.environ.get("NEO4J_URI"),
        "username": os.environ.get("NEO4J_USERNAME"),
        "password": os.environ.get("NEO4J_PASSWORD")
    }
    
    # If any credentials are missing, prompt the user
    if not all(credentials.values()):
        logger.info("Some Neo4j credentials are missing from environment variables or .env file.")
        print("\nNeo4j credentials are required. Please provide the following:")
        
        if not credentials["uri"]:
            credentials["uri"] = input("Neo4j URI [bolt://localhost:7687]: ") or "bolt://localhost:7687"
        
        if not credentials["username"]:
            credentials["username"] = input("Neo4j Username [neo4j]: ") or "neo4j"
        
        if not credentials["password"]:
            import getpass
            credentials["password"] = getpass.getpass("Neo4j Password: ")
    else:
        logger.info("Neo4j credentials loaded from environment variables or .env file.")
    
    return credentials

def create_env_file(credentials: dict):
    """
    Create a .env file with the provided Neo4j credentials.
    
    Args:
        credentials: Dictionary with Neo4j credentials
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # Check if file exists
    file_exists = os.path.exists(env_path)
    
    # Ask for confirmation if file exists
    if file_exists:
        confirm = input("\n.env file already exists. Update with new credentials? (y/n): ").lower()
        if confirm != 'y':
            print("Skipping .env file update.")
            return
    
    with open(env_path, 'w') as f:
        f.write(f"NEO4J_URI={credentials['uri']}\n")
        f.write(f"NEO4J_USERNAME={credentials['username']}\n")
        f.write(f"NEO4J_PASSWORD={credentials['password']}\n")
    
    print(f"\n.env file {'updated' if file_exists else 'created'} successfully at {env_path}")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Run the improved Athenyx ingestion process")
    parser.add_argument("--repo-url", required=True, help="URL of the repository to ingest")
    parser.add_argument("--description", help="Description of the repository")
    parser.add_argument("--clear", action="store_true", help="Clear existing repository data before ingestion")
    parser.add_argument("--force-reindex", action="store_true", help="Force reindexing of the repository even if it exists")
    parser.add_argument("--test-connection", action="store_true", help="Test connection to Neo4j database and exit")
    parser.add_argument("--save-credentials", action="store_true", help="Save Neo4j credentials to .env file")
    
    args = parser.parse_args()
    
    # Get Neo4j credentials
    credentials = get_neo4j_credentials()
    
    # Save credentials to .env file if requested
    if args.save_credentials:
        create_env_file(credentials)
        print("Credentials saved to .env file.")
        if not (args.test_connection or args.repo_url):
            return
    
    # Set environment variables
    os.environ["NEO4J_URI"] = credentials["uri"]
    os.environ["NEO4J_USERNAME"] = credentials["username"]
    os.environ["NEO4J_PASSWORD"] = credentials["password"]
    
    # Test Neo4j connection if requested
    if args.test_connection:
        asyncio.run(test_neo4j_connection())
        sys.exit(0)
    
    # Verify repo URL is provided when not just testing connection
    if not args.repo_url:
        parser.error("--repo-url is required when not using --test-connection or --save-credentials")
    
    # Run the ingestion process
    success = asyncio.run(run_ingestion(
        args.repo_url,
        args.description,
        args.clear,
        args.force_reindex
    ))
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 