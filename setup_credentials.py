#!/usr/bin/env python
"""
Script to set up Neo4j credentials in a .env file.
This simplifies the process of configuring credentials for the ingestion system.
"""
import os
import getpass
import argparse
import re

def setup_credentials(uri=None, username=None, password=None, force=False):
    """
    Set up Neo4j credentials by updating the .env file.
    
    Args:
        uri: Neo4j URI (default: prompt user)
        username: Neo4j username (default: prompt user)
        password: Neo4j password (default: prompt user)
        force: Whether to update credentials without confirmation
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    env_exists = os.path.exists(env_path)
    
    # Check if .env file exists
    if env_exists and not force:
        print(f"A .env file already exists at {env_path}")
        confirm = input("Do you want to update the Neo4j credentials? (y/n): ").lower()
        if confirm != 'y':
            print("Setup canceled.")
            return
    
    # Read existing .env file if it exists
    env_lines = []
    if env_exists:
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Prompt for missing credentials
    if not uri:
        # Try to find current value
        current_uri = None
        for line in env_lines:
            if line.strip().startswith('NEO4J_URI='):
                current_uri = line.strip().split('=', 1)[1]
                break
        default_uri = current_uri or 'bolt://localhost:7687'
        uri = input(f"Neo4j URI [{default_uri}]: ") or default_uri
    
    if not username:
        # Try to find current value
        current_username = None
        for line in env_lines:
            if line.strip().startswith('NEO4J_USERNAME='):
                current_username = line.strip().split('=', 1)[1]
                break
        default_username = current_username or 'neo4j'
        username = input(f"Neo4j Username [{default_username}]: ") or default_username
    
    if not password:
        password = getpass.getpass("Neo4j Password: ")
    
    # Update the .env file
    updated_lines = []
    neo4j_uri_updated = False
    neo4j_username_updated = False
    neo4j_password_updated = False
    
    # Process existing lines
    if env_exists:
        for line in env_lines:
            line_stripped = line.strip()
            if line_stripped.startswith('NEO4J_URI='):
                updated_lines.append(f"NEO4J_URI={uri}\n")
                neo4j_uri_updated = True
            elif line_stripped.startswith('NEO4J_USERNAME='):
                updated_lines.append(f"NEO4J_USERNAME={username}\n")
                neo4j_username_updated = True
            elif line_stripped.startswith('NEO4J_PASSWORD='):
                updated_lines.append(f"NEO4J_PASSWORD={password}\n")
                neo4j_password_updated = True
            else:
                updated_lines.append(line)
    
    # Add any missing Neo4j settings
    if not neo4j_uri_updated:
        if not env_exists or not updated_lines:
            updated_lines.append("# Neo4j Connection\n")
        updated_lines.append(f"NEO4J_URI={uri}\n")
    
    if not neo4j_username_updated:
        updated_lines.append(f"NEO4J_USERNAME={username}\n")
    
    if not neo4j_password_updated:
        updated_lines.append(f"NEO4J_PASSWORD={password}\n")
    
    # Write the updated .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"\nNeo4j credentials {'updated' if env_exists else 'created'} successfully in {env_path}")

def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Set up Neo4j credentials for ingestion system")
    parser.add_argument("--uri", help="Neo4j URI")
    parser.add_argument("--username", help="Neo4j username")
    parser.add_argument("--password", help="Neo4j password (if not provided, will prompt securely)")
    parser.add_argument("--force", action="store_true", help="Update credentials without confirmation")
    parser.add_argument("--test", action="store_true", help="Test connection after setting up credentials")
    
    args = parser.parse_args()
    
    setup_credentials(args.uri, args.username, args.password, args.force)
    
    # Test connection if requested
    if args.test:
        print("\nTesting Neo4j connection...")
        try:
            import asyncio
            from run_ingestion import test_neo4j_connection
            
            success = asyncio.run(test_neo4j_connection())
            if success:
                print("✅ Connection successful!")
            else:
                print("❌ Connection failed.")
                print("Please check your credentials and make sure Neo4j is running.")
        except ImportError:
            print("Could not import test_neo4j_connection. Please run 'python run_ingestion.py --test-connection' to test your connection.")

if __name__ == "__main__":
    main() 