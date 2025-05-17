import asyncio
from app.db.neo4j_manager import db_manager

async def test_neo4j_query():
    try:
        await db_manager.connect()
        
        # Look for README files or documentation
        readme_query = '''
        MATCH (f:File) 
        WHERE f.path CONTAINS "README.md" OR f.is_documentation = true 
        RETURN f.path, f.repo_url
        '''
        readme_results = await db_manager.raw_cypher_query(readme_query)
        print(f'README/documentation files found: {len(readme_results)}')
        for r in readme_results:
            print(r)
            
        # Check for is_documentation flag
        doc_query = '''
        MATCH (f:File) 
        WHERE f.is_documentation = true 
        RETURN f.path, f.repo_url
        '''
        doc_results = await db_manager.raw_cypher_query(doc_query)
        print(f'\nFiles with is_documentation=true: {len(doc_results)}')
        
        # Check CodeChunk nodes connected to README files
        chunk_query = '''
        MATCH (f:File)-[:CONTAINS]->(cc:CodeChunk)
        WHERE f.path CONTAINS "README.md"
        RETURN f.path, count(cc) as chunk_count
        '''
        chunk_results = await db_manager.raw_cypher_query(chunk_query)
        print(f'\nREADME files with code chunks:')
        for r in chunk_results:
            print(f"{r.get('f.path')}: {r.get('chunk_count')} chunks")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(test_neo4j_query()) 