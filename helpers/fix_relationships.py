#!/usr/bin/env python
"""
Script to add missing relationships to existing nodes.
This fixes the structure without trying to create duplicate nodes.
"""
import asyncio
import os
import sys
import logging
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def fix_relationships(repo_url: str):
    """
    Add missing relationships between existing nodes.
    
    Args:
        repo_url: The repository URL to fix relationships for
    """
    from app.db.neo4j_manager import db_manager
    
    logger.info(f"Starting relationship repair process for {repo_url}...")
    
    # 1. Connect to Neo4j
    await db_manager.connect()
    logger.info("Connected to Neo4j database")
    
    # 2. Ensure repository is set as active
    await db_manager.run_query(
        """
        MATCH (r:Repository {url: $url})
        SET r.is_active = true
        RETURN r
        """,
        {"url": repo_url}
    )
    
    # 3. Fix File-Repository relationships
    logger.info("Fixing File-Repository relationships")
    file_result = await db_manager.run_query(
        """
        MATCH (f:File {repo_url: $repo_url})
        MATCH (r:Repository {url: $repo_url})
        WHERE NOT (f)-[:BELONGS_TO]->(r)
        MERGE (f)-[:BELONGS_TO]->(r)
        RETURN count(f) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {file_result[0]['fixed_count']} File-Repository relationships")
    
    # 4. Fix Directory-Repository relationships
    logger.info("Fixing Directory-Repository relationships")
    dir_result = await db_manager.run_query(
        """
        MATCH (d:Directory {repo_url: $repo_url})
        MATCH (r:Repository {url: $repo_url})
        WHERE NOT (d)-[:BELONGS_TO]->(r)
        MERGE (d)-[:BELONGS_TO]->(r)
        RETURN count(d) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {dir_result[0]['fixed_count']} Directory-Repository relationships")
    
    # 5. Fix Directory-File relationships
    logger.info("Fixing Directory-File relationships")
    dir_file_result = await db_manager.run_query(
        """
        // Simple approach using substring
        MATCH (f:File {repo_url: $repo_url})
        WHERE f.path CONTAINS '/'
        WITH f, 
             CASE 
                WHEN f.path CONTAINS '/' 
                THEN substring(f.path, 0, 
                    reduce(idx = -1, c in range(0, size(f.path)) | 
                        CASE WHEN substring(f.path, c, 1) = '/' THEN c ELSE idx END))
            ELSE ''
            END AS dir_path
        WHERE dir_path <> ''
        MATCH (d:Directory {path: dir_path, repo_url: $repo_url})
        WHERE NOT (d)-[:CONTAINS]->(f)
        MERGE (d)-[:CONTAINS]->(f)
        RETURN count(f) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {dir_file_result[0]['fixed_count']} Directory-File relationships")
    
    # 6. Fix parent-child Directory relationships
    logger.info("Fixing parent-child Directory relationships")
    dir_dir_result = await db_manager.run_query(
        """
        MATCH (child:Directory {repo_url: $repo_url})
        WHERE child.path CONTAINS '/'
        WITH child, 
             CASE 
                WHEN child.path CONTAINS '/' 
                THEN substring(child.path, 0, 
                    reduce(idx = -1, c in range(0, size(child.path)) | 
                        CASE WHEN substring(child.path, c, 1) = '/' THEN c ELSE idx END))
                ELSE '' 
             END AS parent_path
        WHERE parent_path <> ''
        MATCH (parent:Directory {path: parent_path, repo_url: $repo_url})
        WHERE NOT (parent)-[:CONTAINS]->(child)
        MERGE (parent)-[:CONTAINS]->(child)
        RETURN count(child) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {dir_dir_result[0]['fixed_count']} parent-child Directory relationships")
    
    # 7. Fix or update Function file_path property and File-Function relationships
    logger.info("Fixing Function-File relationships")

    # First, update Function nodes that are missing file_path but have chunks connected to them
    func_path_result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NULL
        WITH fn
        MATCH (cc:CodeChunk)-[:BELONGS_TO]->(fn)
        WHERE cc.file_path IS NOT NULL
        WITH fn, cc.file_path AS file_path
        LIMIT 1
        SET fn.file_path = file_path
        WITH fn, file_path
        MATCH (f:File {path: file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(fn)
        MERGE (f)-[:CONTAINS]->(fn)
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Updated {func_path_result[0]['fixed_count']} Function file_path properties from connected chunks")

    # Fix Function-File relationships based on file_path property 
    func_file_result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NOT NULL
        WITH fn
        MATCH (f:File {path: fn.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(fn)
        MERGE (f)-[:CONTAINS]->(fn)
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {func_file_result[0]['fixed_count']} Function-File relationships based on file_path")

    # Fix remaining Function-File relationships by matching line ranges
    func_line_result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        WHERE fn.file_path IS NULL
        MATCH (f:File {repo_url: $repo_url})
        MATCH (cc:CodeChunk)
        WHERE cc.parent_id CONTAINS fn.unique_id
        AND cc.file_path = f.path
        AND NOT (f)-[:CONTAINS]->(fn)
        WITH fn, f
        MERGE (f)-[:CONTAINS]->(fn)
        SET fn.file_path = f.path
        RETURN count(fn) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {func_line_result[0]['fixed_count']} Function-File relationships based on code chunks")

    # 8. Fix or update Class file_path property and File-Class relationships
    logger.info("Fixing Class-File relationships")

    # First, update Class nodes that are missing file_path but have chunks connected to them
    class_path_result = await db_manager.run_query(
        """
        MATCH (cl:Class {repo_url: $repo_url})
        WHERE cl.file_path IS NULL
        WITH cl
        MATCH (cc:CodeChunk)-[:BELONGS_TO]->(cl)
        WHERE cc.file_path IS NOT NULL
        WITH cl, cc.file_path AS file_path
        LIMIT 1
        SET cl.file_path = file_path
        WITH cl, file_path
        MATCH (f:File {path: file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(cl)
        MERGE (f)-[:CONTAINS]->(cl)
        RETURN count(cl) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Updated {class_path_result[0]['fixed_count']} Class file_path properties from connected chunks")

    # Fix Class-File relationships based on file_path property
    class_file_result = await db_manager.run_query(
        """
        MATCH (cl:Class {repo_url: $repo_url})
        WHERE cl.file_path IS NOT NULL
        WITH cl
        MATCH (f:File {path: cl.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(cl)
        MERGE (f)-[:CONTAINS]->(cl)
        RETURN count(cl) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {class_file_result[0]['fixed_count']} Class-File relationships based on file_path")

    # Fix remaining Class-File relationships by matching line ranges 
    class_line_result = await db_manager.run_query(
        """
        MATCH (cl:Class {repo_url: $repo_url})
        WHERE cl.file_path IS NULL
        MATCH (f:File {repo_url: $repo_url})
        MATCH (cc:CodeChunk)
        WHERE cc.parent_id CONTAINS cl.unique_id
        AND cc.file_path = f.path
        AND NOT (f)-[:CONTAINS]->(cl)
        WITH cl, f
        MERGE (f)-[:CONTAINS]->(cl)
        SET cl.file_path = f.path
        RETURN count(cl) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {class_line_result[0]['fixed_count']} Class-File relationships based on code chunks")
    
    # 9. Fix CodeChunk-File relationships
    logger.info("Fixing CodeChunk-File relationships")
    chunk_file_result = await db_manager.run_query(
        """
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.file_path IS NOT NULL
        MATCH (f:File {path: cc.file_path, repo_url: $repo_url})
        WHERE NOT (f)-[:CONTAINS]->(cc)
        MERGE (f)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {chunk_file_result[0]['fixed_count']} CodeChunk-File relationships")
    
    # 10. Fix CodeChunk-Repository relationships
    logger.info("Fixing CodeChunk-Repository relationships")
    chunk_repo_result = await db_manager.run_query(
        """
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        MATCH (r:Repository {url: $repo_url})
        WHERE NOT (cc)-[:BELONGS_TO]->(r)
        MERGE (cc)-[:BELONGS_TO]->(r)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {chunk_repo_result[0]['fixed_count']} CodeChunk-Repository relationships")

    # 11. Fix Function-CodeChunk relationships
    logger.info("Fixing Function-CodeChunk relationships")
    func_chunk_result = await db_manager.run_query(
        """
        MATCH (fn:Function {repo_url: $repo_url})
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS fn.unique_id
        AND NOT (fn)-[:CONTAINS]->(cc)
        MERGE (fn)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {func_chunk_result[0]['fixed_count']} Function-CodeChunk relationships")

    # 12. Fix Class-CodeChunk relationships
    logger.info("Fixing Class-CodeChunk relationships")
    class_chunk_result = await db_manager.run_query(
        """
        MATCH (cl:Class {repo_url: $repo_url})
        MATCH (cc:CodeChunk {repo_url: $repo_url})
        WHERE cc.parent_id CONTAINS cl.unique_id
        AND NOT (cl)-[:CONTAINS]->(cc)
        MERGE (cl)-[:CONTAINS]->(cc)
        RETURN count(cc) as fixed_count
        """,
        {"repo_url": repo_url}
    )
    logger.info(f"Fixed {class_chunk_result[0]['fixed_count']} Class-CodeChunk relationships")
    
    logger.info(f"Relationship repair process complete for {repo_url}")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix repository relationships in Neo4j")
    parser.add_argument("--repo-url", required=True, help="Repository URL to fix relationships for")
    
    args = parser.parse_args()
    
    asyncio.run(fix_relationships(args.repo_url))
