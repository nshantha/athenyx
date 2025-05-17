#!/usr/bin/env python
"""
Unified script to fix ontology issues and verify the hierarchical structure:

Repository
  ├── File
  │    ├── Function
  │    │    └── CodeChunk (with embeddings)
  │    ├── Class
  │    │    └── CodeChunk (with embeddings)
  │    └── CodeChunk (with embeddings)
  │
  ├── Service
  │    ├── ApiEndpoint
  │    │    └── Parameters/ReturnTypes
  │    ├── DataModel
  │    └── ServiceInterface
"""
import asyncio
import os
import sys
import logging
import argparse
import json
from tabulate import tabulate
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import fix functions
from fix_class_connections import fix_class_connections
from fix_function_connections import fix_function_connections

async def verify_ontology(db_manager, repo_url: str) -> Dict[str, Any]:
    """
    Verify that the ontology structure matches our desired hierarchy.
    
    Args:
        db_manager: The Neo4j database manager
        repo_url: The repository URL to verify
        
    Returns:
        A dictionary with verification results
    """
    logger.info(f"Verifying ontology structure for {repo_url}...")
    
    results = {}
    
    # Check Repository -> File relationships
    repo_file_result = await db_manager.run_query(
        """
        MATCH (r:Repository {url: $repo_url})
        OPTIONAL MATCH (r)<-[:BELONGS_TO]-(f:File)
        RETURN count(f) as file_count
        """,
        {"repo_url": repo_url}
    )
    results["repository_file_count"] = repo_file_result[0]["file_count"]
    
    # Check File -> Function relationships
    file_func_result = await db_manager.run_query(
        """
        MATCH (f:File {repo_url: $repo_url})
        OPTIONAL MATCH (f)-[:CONTAINS]->(fn:Function)
        RETURN count(DISTINCT fn) as function_count
        """,
        {"repo_url": repo_url}
    )
    results["file_function_count"] = file_func_result[0]["function_count"]
    
    # Check File -> Class relationships
    file_class_result = await db_manager.run_query(
        """
        MATCH (f:File {repo_url: $repo_url})
        OPTIONAL MATCH (f)-[:CONTAINS]->(c:Class)
        RETURN count(DISTINCT c) as class_count
        """,
        {"repo_url": repo_url}
    )
    results["file_class_count"] = file_class_result[0]["class_count"]
    
    # Check Function -> CodeChunk relationships
    func_chunk_result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        OPTIONAL MATCH (fn)-[:CONTAINS]->(cc:CodeChunk)
        RETURN count(DISTINCT cc) as chunk_count
        """,
        {"repo_url": repo_url}
    )
    results["function_chunk_count"] = func_chunk_result[0]["chunk_count"]
    
    # Check Class -> CodeChunk relationships
    class_chunk_result = await db_manager.run_query(
        """
        MATCH (c:Class {repo_url: $repo_url})
        OPTIONAL MATCH (c)-[:CONTAINS]->(cc:CodeChunk)
        RETURN count(DISTINCT cc) as chunk_count
        """,
        {"repo_url": repo_url}
    )
    results["class_chunk_count"] = class_chunk_result[0]["chunk_count"]
    
    # Check File -> CodeChunk (direct) relationships
    file_chunk_result = await db_manager.run_query(
        """
        MATCH (f:File {repo_url: $repo_url})
        OPTIONAL MATCH (f)-[:CONTAINS]->(cc:CodeChunk)
        WHERE NOT EXISTS {
            MATCH (cc)<-[:CONTAINS]-(fn:Function)
        }
        AND NOT EXISTS {
            MATCH (cc)<-[:CONTAINS]-(c:Class)
        }
        RETURN count(DISTINCT cc) as direct_chunk_count
        """,
        {"repo_url": repo_url}
    )
    results["file_direct_chunk_count"] = file_chunk_result[0]["direct_chunk_count"]
    
    # Check orphaned chunks (chunks without any parent)
    orphan_chunk_result = await db_manager.run_query(
        """
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE NOT EXISTS {
            MATCH (cc)<-[:CONTAINS]-(f:File)
        }
        AND NOT EXISTS {
            MATCH (cc)<-[:CONTAINS]-(fn:Function)
        }
        AND NOT EXISTS {
            MATCH (cc)<-[:CONTAINS]-(c:Class)
        }
        RETURN count(cc) as orphan_count
        """,
        {"repo_url": repo_url}
    )
    results["orphaned_chunk_count"] = orphan_chunk_result[0]["orphan_count"]
    
    # Collect total node counts
    node_counts = await db_manager.run_query(
        """
        MATCH (n)
        WHERE n.repo_url = $repo_url OR n.url = $repo_url
        RETURN labels(n) as type, count(n) as count
        ORDER BY count DESC
        """,
        {"repo_url": repo_url}
    )
    
    node_count_dict = {}
    for record in node_counts:
        node_type = record["type"][0] if isinstance(record["type"], list) else record["type"]
        node_count_dict[node_type] = record["count"]
    
    results["node_counts"] = node_count_dict
    
    # Check completeness percentages
    total_functions = node_count_dict.get("Function", 0)
    total_classes = node_count_dict.get("Class", 0)
    total_chunks = node_count_dict.get("CodeChunk", 0)
    
    results["function_file_connection_percentage"] = (
        (results["file_function_count"] / total_functions * 100) 
        if total_functions > 0 else 0
    )
    
    results["class_file_connection_percentage"] = (
        (results["file_class_count"] / total_classes * 100) 
        if total_classes > 0 else 0
    )
    
    results["function_chunk_connection_percentage"] = (
        (results["function_chunk_count"] / total_chunks * 100) 
        if total_chunks > 0 else 0
    )
    
    results["class_chunk_connection_percentage"] = (
        (results["class_chunk_count"] / total_chunks * 100) 
        if total_chunks > 0 else 0
    )
    
    results["direct_file_chunk_connection_percentage"] = (
        (results["file_direct_chunk_count"] / total_chunks * 100) 
        if total_chunks > 0 else 0
    )
    
    results["orphaned_chunk_percentage"] = (
        (results["orphaned_chunk_count"] / total_chunks * 100) 
        if total_chunks > 0 else 0
    )
    
    return results

def print_verification_results(results: Dict[str, Any]):
    """Print the verification results in a readable format"""
    logger.info("Ontology Verification Results:")
    
    # Node counts table
    node_counts = [
        [node_type, count] 
        for node_type, count in results.get("node_counts", {}).items()
    ]
    print("\nNode Counts:")
    print(tabulate(node_counts, headers=["Node Type", "Count"]))
    
    # Relationship counts table
    relationship_counts = [
        ["Repository -> File", results.get("repository_file_count", 0)],
        ["File -> Function", results.get("file_function_count", 0)],
        ["File -> Class", results.get("file_class_count", 0)],
        ["Function -> CodeChunk", results.get("function_chunk_count", 0)],
        ["Class -> CodeChunk", results.get("class_chunk_count", 0)],
        ["File -> CodeChunk (direct)", results.get("file_direct_chunk_count", 0)],
        ["Orphaned CodeChunks", results.get("orphaned_chunk_count", 0)]
    ]
    print("\nRelationship Counts:")
    print(tabulate(relationship_counts, headers=["Relationship", "Count"]))
    
    # Connection percentages table
    connection_percentages = [
        ["Function -> File Connection", f"{results.get('function_file_connection_percentage', 0):.2f}%"],
        ["Class -> File Connection", f"{results.get('class_file_connection_percentage', 0):.2f}%"],
        ["Function -> CodeChunk Connection", f"{results.get('function_chunk_connection_percentage', 0):.2f}%"],
        ["Class -> CodeChunk Connection", f"{results.get('class_chunk_connection_percentage', 0):.2f}%"],
        ["File -> CodeChunk (direct) Connection", f"{results.get('direct_file_chunk_connection_percentage', 0):.2f}%"],
        ["Orphaned CodeChunks", f"{results.get('orphaned_chunk_percentage', 0):.2f}%"]
    ]
    print("\nConnection Percentages:")
    print(tabulate(connection_percentages, headers=["Connection Type", "Percentage"]))

async def run_ontology_fix_and_verify(repo_url: str, verify_only: bool = False):
    """
    Run all fixes and verify the ontology structure.
    
    Args:
        repo_url: The repository URL to fix and verify
        verify_only: If True, only verify the ontology without applying fixes
    """
    from app.db.neo4j_manager import db_manager
    
    try:
        await db_manager.connect()
        logger.info("Connected to Neo4j database")
        
        # Verify before fixes
        logger.info("Verifying ontology structure before fixes...")
        before_results = await verify_ontology(db_manager, repo_url)
        print_verification_results(before_results)
        
        if not verify_only:
            # Run fixes
            logger.info("Running ontology fixes...")
            await fix_class_connections(repo_url)
            await fix_function_connections(repo_url)
            
            # Verify after fixes
            logger.info("Verifying ontology structure after fixes...")
            after_results = await verify_ontology(db_manager, repo_url)
            print_verification_results(after_results)
            
            # Save results to file
            with open("ontology_verification_results.json", "w") as f:
                json.dump({
                    "before": before_results,
                    "after": after_results
                }, f, indent=2)
                
            logger.info("Saved verification results to ontology_verification_results.json")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        await db_manager.close()

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix and verify ontology structure in Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to fix and verify")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the ontology without applying fixes")
    
    args = parser.parse_args()
    
    asyncio.run(run_ontology_fix_and_verify(args.repo_url, args.verify_only)) 