from app.db.neo4j_manager import db_manager
import asyncio

async def check_readme():
    await db_manager.connect()
    
    # Check if any CodeChunk nodes exist
    results = await db_manager.raw_cypher_query('MATCH (cc:CodeChunk) RETURN count(cc) as count')
    if results:
        print(f'Total CodeChunk nodes: {results[0].get("count")}')
    
    # Get a sample node to check all available properties
    print("\nChecking properties on CodeChunk nodes...")
    sample_node = await db_manager.raw_cypher_query('MATCH (cc:CodeChunk) RETURN cc LIMIT 1')
    if sample_node and len(sample_node) > 0:
        node = sample_node[0].get('cc')
        print("Available properties:")
        for key in node.keys():
            print(f"- {key}")
            
        # Check sample values
        for key in node.keys():
            if key != 'embedding':  # Skip embedding as it's too large
                value = node.get(key)
                print(f"{key}: {value}")
    
    # Check how many chunks have embeddings
    embedding_count = await db_manager.raw_cypher_query('MATCH (cc:CodeChunk) WHERE cc.embedding IS NOT NULL RETURN count(cc) as count')
    if embedding_count:
        print(f'\nCodeChunks with embeddings: {embedding_count[0].get("count")}')
    
    # Check if any chunks have content property
    content_query = await db_manager.raw_cypher_query('MATCH (cc:CodeChunk) WHERE cc.content IS NOT NULL RETURN count(cc) as count')
    if content_query:
        print(f'CodeChunks with content: {content_query[0].get("count")}')
    
    # Check the repository structure
    print("\nChecking repository structure...")
    repo_results = await db_manager.raw_cypher_query('MATCH (r:Repository) RETURN r, labels(r) as labels LIMIT 1')
    if repo_results and len(repo_results) > 0:
        repo_node = repo_results[0].get('r')
        labels = repo_results[0].get('labels')
        print(f'Repository labels: {labels}')
        print("Repository properties:")
        for key in repo_node.keys():
            print(f"- {key}: {repo_node.get(key)}")
    
    # Check if the vector index exists
    index_query = await db_manager.raw_cypher_query("SHOW INDEXES WHERE name = 'code_chunk_embeddings'")
    print(f"\nVector index exists: {len(index_query) > 0}")
    
    # Check the actual query used by the retriever
    print("\nChecking Neo4jCodeRetriever implementation...")
    retriever_query = """
    CALL db.index.vector.queryNodes(
        'code_chunk_embeddings',
        $k,
        $query_embedding
    ) YIELD node, score
    MATCH (node:CodeChunk)
    RETURN node.content as text, node.file_path as path, score
    LIMIT $k
    """
    print(f"Retriever query: {retriever_query}")
    
    await db_manager.close()

if __name__ == "__main__":
    asyncio.run(check_readme()) 