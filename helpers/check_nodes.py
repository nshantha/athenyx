#!/usr/bin/env python
import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

async def main():
    # Get Neo4j credentials from environment variables
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    print(f"Connecting to Neo4j at {neo4j_uri}...")
    driver = AsyncGraphDatabase.driver(
        neo4j_uri, 
        auth=(neo4j_username, neo4j_password)
    )
    
    try:
        async with driver.session() as session:
            # Check what node types exist and their counts
            print("\n=== Node Types in Database ===")
            result = await session.run(
                """
                MATCH (n) 
                RETURN distinct labels(n) as type, count(*) as count 
                ORDER BY count DESC
                """
            )
            records = await result.values()
            for record in records:
                print(f"{record[0]}: {record[1]}")
                
            # Check if there are any Function nodes
            print("\n=== Function Nodes ===")
            result = await session.run(
                """
                MATCH (f:Function)
                RETURN f.name as name, f.path as path
                LIMIT 10
                """
            )
            records = await result.values()
            if not records:
                print("No Function nodes found.")
            else:
                for record in records:
                    print(f"Function: {record[0]} in {record[1]}")
                
            # Check if there are any Class nodes
            print("\n=== Class Nodes ===")
            result = await session.run(
                """
                MATCH (c:Class)
                RETURN c.name as name, c.path as path
                LIMIT 10
                """
            )
            records = await result.values()
            if not records:
                print("No Class nodes found.")
            else:
                for record in records:
                    print(f"Class: {record[0]} in {record[1]}")
                    
            # Check relationships between nodes
            print("\n=== Relationship Types ===")
            result = await session.run(
                """
                MATCH ()-[r]->() 
                RETURN distinct type(r) as relation, count(*) as count 
                ORDER BY count DESC
                """
            )
            records = await result.values()
            for record in records:
                print(f"{record[0]}: {record[1]}")
                
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(main()) 