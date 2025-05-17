#!/usr/bin/env python
import asyncio
import os
import sys
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def main():
    # Get Neo4j credentials from environment variables
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_password:
        print("Error: NEO4J_PASSWORD environment variable is not set.")
        print("Please run 'python setup_credentials.py' first to set up your Neo4j credentials.")
        sys.exit(1)
    
    print("Connecting to Neo4j...")
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
    
    try:
        # Test the connection
        await driver.verify_connectivity()
        print(f"Connected to Neo4j at {neo4j_uri}")
    
    print("Cleaning database...")
    # Delete all relationships first
        async with driver.session() as session:
            await session.run('MATCH ()-[r]-() DELETE r')
    print("All relationships deleted")
    
    # Delete all nodes
            await session.run('MATCH (n) DELETE n')
    print("All nodes deleted")
    
        print("Database cleaned successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Close the connection
        await driver.close()

if __name__ == "__main__":
    asyncio.run(main()) 