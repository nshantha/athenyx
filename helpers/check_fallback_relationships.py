#!/usr/bin/env python
"""
Script to check for fallback relationships between CodeChunk nodes and Repository nodes.
Helps evaluate optimization efforts to reduce direct connections that bypass proper hierarchy.
"""
import asyncio
import os
import sys
import logging
import argparse
import json
from tabulate import tabulate

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def check_fallback_relationships(db_manager, repo_url: str):
    """
    Check for fallback relationships between CodeChunks and Repository, bypassing File nodes.
    
    Args:
        db_manager: The Neo4j database manager
        repo_url: The repository URL to check
        
    Returns:
        Dictionary with counts of fallback relationships
    """
    logger.info(f"Checking fallback relationships for {repo_url}...")
    
    # Get count of CodeChunks directly connected to Repository (fallbacks)
    fallback_query = """
    MATCH (r:Repository {url: $repo_url})-[:CONTAINS]->(cc:CodeChunk)
    WHERE NOT exists((cc)<-[:CONTAINS]-(:File))
    AND NOT exists((cc)<-[:CONTAINS]-(:Function))
    AND NOT exists((cc)<-[:CONTAINS]-(:Class))
    RETURN count(cc) as fallback_count
    """
    
    fallback_result = await db_manager.run_query(fallback_query, {"repo_url": repo_url})
    fallback_count = fallback_result[0]["fallback_count"] if fallback_result else 0
    
    # Get total CodeChunk count
    total_query = """
    MATCH (cc:CodeChunk {repo_url: $repo_url})
    RETURN count(cc) as total_count
    """
    
    total_result = await db_manager.run_query(total_query, {"repo_url": repo_url})
    total_count = total_result[0]["total_count"] if total_result else 0
    
    # Get counts by connection type
    connection_query = """
    MATCH (cc:CodeChunk {repo_url: $repo_url})
    RETURN
        count(cc) as total,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:File)) THEN cc END) as file_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Function)) THEN cc END) as function_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Class)) THEN cc END) as class_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Repository)) THEN cc END) as repo_connected
    """
    
    connection_result = await db_manager.run_query(connection_query, {"repo_url": repo_url})
    connection_counts = connection_result[0] if connection_result else {}
    
    # Get proto file relationship counts
    proto_query = """
    MATCH (cc:CodeChunk {repo_url: $repo_url})
    WHERE cc.file_path ENDS WITH '.proto'
    RETURN
        count(cc) as total_proto,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:File)) THEN cc END) as file_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Function)) THEN cc END) as function_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Class)) THEN cc END) as class_connected,
        count(CASE WHEN exists((cc)<-[:CONTAINS]-(:Repository)) THEN cc END) as repo_connected
    """
    
    proto_result = await db_manager.run_query(proto_query, {"repo_url": repo_url})
    proto_counts = proto_result[0] if proto_result else {}
    
    return {
        "fallback_count": fallback_count,
        "total_count": total_count,
        "fallback_percentage": (fallback_count / total_count * 100) if total_count > 0 else 0,
        "connection_counts": connection_counts,
        "proto_counts": proto_counts
    }

def print_results(results):
    """Print the check results in a readable format"""
    logger.info("Fallback Relationship Check Results:")
    
    print(f"\nTotal CodeChunks: {results['total_count']}")
    print(f"Fallback Relationships: {results['fallback_count']} " +
          f"({results['fallback_percentage']:.2f}%)")
    
    # Connection counts
    conn_counts = results.get("connection_counts", {})
    conn_table = [
        ["Connected to File", conn_counts.get("file_connected", 0)],
        ["Connected to Function", conn_counts.get("function_connected", 0)],
        ["Connected to Class", conn_counts.get("class_connected", 0)],
        ["Connected directly to Repository", conn_counts.get("repo_connected", 0)]
    ]
    print("\nConnection Distribution:")
    print(tabulate(conn_table, headers=["Connection Type", "Count"]))
    
    # Proto file counts
    proto_counts = results.get("proto_counts", {})
    if proto_counts.get("total_proto", 0) > 0:
        proto_table = [
            ["Total Proto Chunks", proto_counts.get("total_proto", 0)],
            ["Connected to File", proto_counts.get("file_connected", 0)],
            ["Connected to Function", proto_counts.get("function_connected", 0)],
            ["Connected to Class", proto_counts.get("class_connected", 0)],
            ["Connected directly to Repository", proto_counts.get("repo_connected", 0)]
        ]
        print("\nProtobuf File Chunks:")
        print(tabulate(proto_table, headers=["Connection Type", "Count"]))

async def run_check(repo_url: str, save_results: bool = False):
    """
    Run the check for fallback relationships.
    
    Args:
        repo_url: The repository URL to check
        save_results: Whether to save the results to a file
    """
    from app.db.neo4j_manager import db_manager
    
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        # Run the check
        results = await check_fallback_relationships(db_manager, repo_url)
        
        # Print the results
        print_results(results)
        
        # Save results to file if requested
        if save_results:
            filename = f"fallback_check_{repo_url.split('/')[-1].replace('.git', '')}.json"
            with open(filename, "w") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved results to {filename}")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check for fallback relationships in Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to check")
    parser.add_argument("--save", action="store_true", help="Save results to a file")
    
    args = parser.parse_args()
    
    asyncio.run(run_check(args.repo_url, args.save)) 