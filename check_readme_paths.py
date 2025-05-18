from app.db.neo4j_manager import db_manager
import asyncio

async def check_readme_paths():
    await db_manager.connect()
    
    # Check for README files in File nodes
    file_results = await db_manager.raw_cypher_query('MATCH (f:File) WHERE f.path CONTAINS "README" OR f.repo_url CONTAINS "microservices-demo" RETURN f LIMIT 5')
    print(f'Found {len(file_results)} File nodes')
    for i, r in enumerate(file_results):
        node = r.get("f")
        print(f"\nFile node {i+1}:")
        for key in node.keys():
            print(f"  - {key}: {node.get(key)}")
    
    # Check for README files in CodeChunk nodes
    chunk_results = await db_manager.raw_cypher_query('MATCH (cc:CodeChunk) WHERE cc.content CONTAINS "README" OR cc.content CONTAINS "microservices" RETURN cc LIMIT 5')
    print(f'\nFound {len(chunk_results)} CodeChunk nodes')
    for i, r in enumerate(chunk_results):
        node = r.get("cc")
        print(f"\nCodeChunk node {i+1}:")
        for key in node.keys():
            if key != "embedding" and key != "content":
                print(f"  - {key}: {node.get(key)}")
        if "content" in node:
            content = node.get("content")
            if content:
                print(f"  - content: {content[:100]}...")
            else:
                print("  - content: None")
    
    # Check repository information
    repo_results = await db_manager.raw_cypher_query('MATCH (r:Repository) RETURN r LIMIT 5')
    print(f'\nFound {len(repo_results)} Repository nodes')
    for i, r in enumerate(repo_results):
        node = r.get("r")
        print(f"\nRepository node {i+1}:")
        for key in node.keys():
            print(f"  - {key}: {node.get(key)}")
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_readme_paths()) 