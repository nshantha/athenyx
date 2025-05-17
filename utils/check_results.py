#!/usr/bin/env python
"""
Script to check the results of our ingestion changes
"""
import asyncio
from app.db.neo4j_manager import db_manager

async def check_ingestion_results():
    """Check the results of our ingestion changes"""
    await db_manager.connect()
    
    try:
        # Check all files by extension to see what was ingested
        for ext in ['.md', '.proto', '.json', '.yaml', '.yml', '.go', '.py', '.js']:
            files_query = f"""
            MATCH (f:File) 
            WHERE f.path ENDS WITH '{ext}' AND f.repo_url CONTAINS 'microservices-demo' 
            RETURN count(f) as file_count
            """
            files = await db_manager.run_query(files_query)
            print(f'{ext} files: {files[0]["file_count"] if files else 0}')
        
        # Check for documentation files
        docs_query = """
        MATCH (f:File) 
        WHERE f.is_documentation = true AND f.repo_url CONTAINS 'microservices-demo' 
        RETURN f.path AS path LIMIT 10
        """
        docs = await db_manager.run_query(docs_query)
        print("\nSample Documentation Files:")
        for doc in docs:
            print(f"- {doc['path'].split('/')[-1]} ({doc['path']})")
        
        # Check for protobuf files specifically
        proto_query = """
        MATCH (f:File) 
        WHERE f.language = 'protobuf' AND f.repo_url CONTAINS 'microservices-demo' 
        RETURN f.path AS path LIMIT 10
        """
        protos = await db_manager.run_query(proto_query)
        print("\nProtobuf Files:")
        for proto in protos:
            print(f"- {proto['path']}")
        
        # Check for data models
        models_query = """
        MATCH (m:Class) 
        WHERE m.is_data_model = true OR m.type = 'message' AND m.repo_url CONTAINS 'microservices-demo' 
        RETURN count(m) as model_count
        """
        models = await db_manager.run_query(models_query)
        print(f"\nData models: {models[0]['model_count'] if models else 0}")

        # If there are data models, show some examples
        if models and models[0]['model_count'] > 0:
            models_examples_query = """
            MATCH (m:Class) 
            WHERE (m.is_data_model = true OR m.type = 'message') AND m.repo_url CONTAINS 'microservices-demo' 
            RETURN m.name AS name, m.path AS path LIMIT 5
            """
            model_examples = await db_manager.run_query(models_examples_query)
            print("\nSample Data Models:")
            for model in model_examples:
                print(f"- {model['name']} ({model['path']})")
        
        # Check for API endpoints
        apis_query = """
        MATCH (a:Class) 
        WHERE a.is_api = true OR a.type = 'service' AND a.repo_url CONTAINS 'microservices-demo' 
        RETURN count(a) as api_count
        """
        apis = await db_manager.run_query(apis_query)
        print(f"\nAPI endpoints: {apis[0]['api_count'] if apis else 0}")

        # If there are API endpoints, show some examples
        if apis and apis[0]['api_count'] > 0:
            apis_examples_query = """
            MATCH (a:Class) 
            WHERE (a.is_api = true OR a.type = 'service') AND a.repo_url CONTAINS 'microservices-demo' 
            RETURN a.name AS name, a.path AS path LIMIT 5
            """
            api_examples = await db_manager.run_query(apis_examples_query)
            print("\nSample API Endpoints:")
            for api in api_examples:
                print(f"- {api['name']} ({api['path']})")

    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_ingestion_results()) 