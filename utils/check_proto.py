#!/usr/bin/env python
"""
Script to check for protobuf files in Neo4j and diagnose issues
"""
import asyncio
from app.db.neo4j_manager import db_manager

async def check_proto_files():
    """Check for protobuf files and related entities in Neo4j"""
    await db_manager.connect()
    
    try:
        # Check for protobuf files in the File nodes
        print("Checking for protobuf files in Neo4j...")
        proto_files_query = """
        MATCH (f:File) 
        WHERE f.path ENDS WITH '.proto' OR f.language = 'protobuf'
        RETURN f.path, f.language, f.parse_error
        """
        proto_files = await db_manager.run_query(proto_files_query)
        
        if not proto_files:
            print("No protobuf files found in Neo4j")
        else:
            print(f"Found {len(proto_files)} protobuf files:")
            for file in proto_files:
                print(f"- {file['f.path']} (language: {file['f.language']}, parse_error: {file['f.parse_error']})")
        
        # Check for any classes with protobuf-related properties
        print("\nChecking for protobuf-related Class nodes...")
        proto_classes_query = """
        MATCH (c:Class)
        WHERE c.file_path ENDS WITH '.proto' OR c.type = 'message' OR c.type = 'service'
        RETURN c.name, c.type, c.file_path, c.is_data_model, c.is_api
        """
        proto_classes = await db_manager.run_query(proto_classes_query)
        
        if not proto_classes:
            print("No protobuf-related Class nodes found")
        else:
            print(f"Found {len(proto_classes)} protobuf-related Class nodes:")
            for cls in proto_classes:
                print(f"- {cls['c.name']} (type: {cls['c.type']}, file: {cls['c.file_path']}, is_data_model: {cls['c.is_data_model']}, is_api: {cls['c.is_api']})")
        
        # Check for all properties on Class nodes to diagnose issues
        print("\nChecking properties on Class nodes...")
        class_props_query = """
        MATCH (c:Class)
        RETURN DISTINCT keys(c) as properties
        LIMIT 1
        """
        class_props = await db_manager.run_query(class_props_query)
        
        if class_props:
            print("Properties available on Class nodes:")
            for prop in class_props[0]['properties']:
                print(f"- {prop}")
        
        # Check for any nodes with protobuf file paths
        print("\nChecking for any nodes with protobuf file paths...")
        proto_path_query = """
        MATCH (n)
        WHERE n.path ENDS WITH '.proto' OR n.file_path ENDS WITH '.proto'
        RETURN labels(n) as type, n.path, n.file_path
        LIMIT 10
        """
        proto_paths = await db_manager.run_query(proto_path_query)
        
        if not proto_paths:
            print("No nodes with protobuf file paths found")
        else:
            print(f"Found {len(proto_paths)} nodes with protobuf file paths:")
            for node in proto_paths:
                path = node.get('n.path', node.get('n.file_path', 'Unknown'))
                print(f"- {node['type']}: {path}")
                
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_proto_files()) 