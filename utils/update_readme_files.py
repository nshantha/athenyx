import asyncio
import os
from app.db.neo4j_manager import db_manager
from ingestion.processing.embedding import generate_embedding

async def update_readme_files():
    """Update existing File nodes in Neo4j to set is_documentation=true for README files and create chunks for them."""
    try:
        print("Connecting to Neo4j database...")
        await db_manager.connect()
        
        # 1. Add is_documentation property to the database schema
        print("Adding is_documentation property to File nodes...")
        # Get all README and documentation files
        readme_query = """
        MATCH (f:File)
        WHERE f.path CONTAINS 'README' OR 
              f.path CONTAINS '.md' OR 
              f.path CONTAINS '/docs/' OR
              f.path CONTAINS '/documentation/'
        RETURN f.path, f.repo_url
        """
        readme_files = await db_manager.raw_cypher_query(readme_query)
        print(f"Found {len(readme_files)} potential documentation files")
        
        # 2. Set is_documentation=true for these files
        for file in readme_files:
            path = file.get('f.path')
            repo_url = file.get('f.repo_url')
            
            if not path or not repo_url:
                print(f"Skipping file with missing path or repo_url: {file}")
                continue
                
            update_query = """
            MATCH (f:File {path: $path, repo_url: $repo_url})
            SET f.is_documentation = true
            RETURN f.path
            """
            params = {"path": path, "repo_url": repo_url}
            result = await db_manager.run_query(update_query, params)
            print(f"Updated file: {path}")
            
            # 3. For README files specifically, check if they have chunks
            if "README" in path.upper():
                chunks_query = """
                MATCH (f:File {path: $path})-[:CONTAINS]->(cc:CodeChunk)
                RETURN count(cc) as chunk_count
                """
                chunks_params = {"path": path}
                chunks_result = await db_manager.run_query(chunks_query, chunks_params)
                
                chunk_count = 0
                if chunks_result and len(chunks_result) > 0:
                    chunk_count = chunks_result[0].get("chunk_count", 0)
                
                print(f"README file {path} has {chunk_count} chunks")
                
                # 4. If a README has no chunks, create them directly
                if chunk_count == 0:
                    print(f"Creating chunks for README file: {path}")
                    await create_readme_chunks(path, repo_url)
        
        # 5. Verify updates
        verify_query = """
        MATCH (f:File)
        WHERE f.is_documentation = true
        RETURN count(f) as doc_count
        """
        verify_result = await db_manager.run_query(verify_query)
        doc_count = verify_result[0]["doc_count"] if verify_result else 0
        print(f"Total files marked as documentation: {doc_count}")
        
    except Exception as e:
        print(f"Error updating README files: {e}")
    finally:
        await db_manager.close()

async def create_readme_chunks(path, repo_url):
    """Create chunks for a README file that doesn't have any."""
    try:
        # Extract repo name from URL for folder path
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        
        # Try to find the file in the local filesystem
        local_path = f"ingestion/repos/{repo_name}/{path}"
        if not os.path.exists(local_path):
            print(f"README file not found at {local_path}")
            return
            
        # Read the file content
        with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        if not content.strip():
            print(f"README file {path} is empty")
            return
            
        # Create chunks - simple approach for demonstration
        from langchain_text_splitters import MarkdownTextSplitter
        splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(content)
        
        print(f"Creating {len(chunks)} chunks for README {path}")
        
        # Get service name from repo URL
        service_name = repo_name
        
        # Create chunk nodes with embeddings
        for i, chunk_text in enumerate(chunks):
            chunk_id = f"readme::{repo_name}::{path}::{i}"
            
            # Create embedding for the chunk
            embedding = await generate_embedding(chunk_text)
            
            # Estimate line ranges (not accurate but helps with ordering)
            start_line = i * 10
            end_line = start_line + chunk_text.count('\n') + 1
            
            # Create a chunk node and connect it to the file
            create_query = """
            MERGE (cc:CodeChunk {chunk_id: $chunk_id})
            SET cc.content = $content,
                cc.start_line = $start_line,
                cc.end_line = $end_line,
                cc.repo_url = $repo_url,
                cc.service_name = $service_name,
                cc.embedding = $embedding,
                cc.parent_type = 'File',
                cc.is_readme = true
            WITH cc
            MATCH (f:File {path: $path, repo_url: $repo_url})
            MERGE (f)-[:CONTAINS]->(cc)
            """
            
            create_params = {
                "chunk_id": chunk_id,
                "content": chunk_text,
                "start_line": start_line,
                "end_line": end_line,
                "repo_url": repo_url,
                "service_name": service_name,
                "embedding": embedding,
                "path": path
            }
            
            await db_manager.run_query(create_query, create_params)
            
        print(f"Successfully created README chunks for {path}")
    except Exception as e:
        print(f"Error creating README chunks for {path}: {e}")

if __name__ == "__main__":
    asyncio.run(update_readme_files()) 