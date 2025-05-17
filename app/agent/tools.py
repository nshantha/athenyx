# app/agent/tools.py
import logging
from typing import List, Dict, Any
from langchain_core.tools import Tool
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import CallbackManagerForRetrieverRun, AsyncCallbackManagerForRetrieverRun # Import Async manager
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI # Keep import if needed elsewhere, though LLM is defined in graph.py
from langchain_community.tools.tavily_search import TavilySearchResults
import asyncio # Import asyncio for the sync wrapper

from app.db.neo4j_manager import db_manager # Import the instantiated manager
from app.core.config import settings
from app.schemas.models import ChunkResult

logger = logging.getLogger(__name__)

# --- Custom Neo4j Vector Retriever ---
class Neo4jCodeRetriever(BaseRetriever):
    """Custom LangChain retriever for Neo4j vector search results."""
    k: int = 10  # Increased from 5 to get more context for high-level questions

    # --- FIX: Add the synchronous method implementation ---
    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        """Synchronously retrieves relevant documents.
           NOTE: This is a wrapper around the async version for compatibility.
                 Consider implementing natively sync logic if performance is critical
                 and async is not strictly needed everywhere.
        """
        # Simple way: Run the async version using asyncio.run()
        # Be cautious using asyncio.run() inside an already running event loop
        # A better approach might involve checking if a loop is running or using a thread.
        # For simplicity now, let's raise NotImplementedError or run it simply.
        logger.warning("Running Neo4j retriever synchronously (wrapping async call).")
        try:
            # This might cause issues if called from within an existing async context/event loop.
            # A dedicated synchronous DB query method might be safer if needed.
            return asyncio.run(self._aget_relevant_documents(query, run_manager=run_manager)) # Use run_manager here if needed by async method's interface
            # Alternatively, raise error if sync use is unexpected:
            # raise NotImplementedError("Synchronous retrieval not implemented directly. Use aget_relevant_documents.")
        except RuntimeError as e:
             logger.error(f"RuntimeError calling async retriever from sync: {e}. This might happen if called from within an event loop.")
             return []


    # --- Keep the Asynchronous method ---
    async def _aget_relevant_documents(
        self, query: str, *, run_manager: AsyncCallbackManagerForRetrieverRun # Use Async manager type hint
    ) -> List[Document]:
        """Asynchronously retrieves relevant documents from Neo4j vector index."""
        
        # Detect query type
        query_lower = query.lower()
        is_high_level = any(term in query_lower for term in [
            "overview", "about", "what is", "purpose", "high-level", "features", 
            "how many", "architecture", "summary", "microservices", "services"
        ])
        
        # Adjust k based on query type (more results for high-level queries)
        search_k = 20 if is_high_level else self.k
        
        # 1. Embed the query
        try:
            from ingestion.processing.embedding import aclient as openai_aclient # Re-use client
            response = await openai_aclient.embeddings.create(
                input=[query],
                model=settings.openai_embedding_model
            )
            query_embedding = response.data[0].embedding
            logger.debug(f"Successfully embedded query for retrieval.")
        except Exception as e:
             logger.error(f"Failed to embed query '{query}': {e}", exc_info=True)
             return []

        # 2. Get the active repository for prioritization
        active_repo = await db_manager.get_active_repository()
        active_repo_url = active_repo.get('url') if active_repo else None
        
        # 3. Perform vector search
        try:
            # Try to use a specific Neo4j query for high-level project info if available
            if is_high_level and "microservices" in query_lower or "services" in query_lower:
                # Special handling for microservices questions to ensure consistency
                try:
                    # Try a more targeted query that focuses on README content or specific files
                    special_results = await db_manager.query_high_level_info("microservices")
                    if special_results and len(special_results) > 0:
                        logger.info(f"Using specialized high-level query for microservices information")
                        documents = []
                        for result in special_results:
                            metadata = {
                                "source": result.get("path", "unknown"),
                                "score": 1.0,  # Assign high confidence
                                "special_query": True
                            }
                            doc = Document(page_content=result.get("text", ""), metadata=metadata)
                            documents.append(doc)
                        
                        # Use regular vector search as a fallback if special query returns minimal results
                        if len(documents) < 2:
                            logger.info("Special query returned minimal results, falling back to vector search")
                        else:
                            return documents
                except Exception as e:
                    logger.error(f"Error in specialized high-level query: {e}", exc_info=True)
                    # Continue with regular vector search
            
            # Standard vector search with repository prioritization
            if active_repo_url:
                # First search in the active repository
                primary_results = await db_manager.vector_search_code_chunks(
                    query_embedding=query_embedding,
                    k=search_k,
                    repository_url=active_repo_url  # Limit to active repository
                )
                logger.debug(f"Primary repository search returned {len(primary_results)} results.")
                
                # If primary search has insufficient results, check connected repositories
                if len(primary_results) < 3:
                    logger.info(f"Primary repository search returned limited results, checking connected repositories")
                    
                    # Get connected repositories
                    connected_repos = await db_manager.get_connected_repositories(active_repo_url)
                    connected_repo_urls = [repo.get('url') for repo in connected_repos]
                    
                    if connected_repo_urls:
                        # Search in connected repositories
                        secondary_results = []
                        for repo_url in connected_repo_urls:
                            repo_results = await db_manager.vector_search_code_chunks(
                                query_embedding=query_embedding,
                                k=5,  # Fewer results from secondary repositories
                                repository_url=repo_url
                            )
                            # Tag results with repository info
                            for result in repo_results:
                                result['secondary_repo'] = True
                                result['repo_url'] = repo_url
                                result['repo_name'] = repo_url.split('/')[-1].replace('.git', '')
                            
                            secondary_results.extend(repo_results)
                        
                        logger.debug(f"Secondary repositories search returned {len(secondary_results)} results.")
                        
                        # Combine results, prioritizing primary repository
                        search_results = primary_results + secondary_results
                    else:
                        search_results = primary_results
                else:
                    search_results = primary_results
            else:
                # If no active repository, search across all repositories
                search_results = await db_manager.vector_search_code_chunks(
                    query_embedding=query_embedding,
                    k=search_k
                )
                
            logger.debug(f"Total vector search returned {len(search_results)} results.")
        except Exception as e:
            logger.error(f"Failed to retrieve from Neo4j vector index: {e}", exc_info=True)
            return []

        # 4. Process results
        documents = []
        for result in search_results:
            text = result.get("text", "")
            path = result.get("path", "unknown")
            
            # Add score boosting for README files for high-level queries
            score_boost = 1.0
            if is_high_level and ("README" in path or "readme" in path):
                score_boost = 1.5
            
            # Lower score for secondary repository results
            if result.get('secondary_repo'):
                score_boost *= 0.8
                
            metadata = {
                "source": path,
                "score": result.get("score", 0) * score_boost,
                "start_line": result.get("start_line"),
                "is_high_level": is_high_level,
                "secondary_repo": result.get('secondary_repo', False),
                "repo_url": result.get('repo_url'),
                "repo_name": result.get('repo_name')
            }
            metadata = {k: v for k, v in metadata.items() if v is not None}
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)

        # 5. Sort by boosted score for consistency
        documents.sort(key=lambda x: x.metadata.get("score", 0), reverse=True)
        
        # 6. Add special handling for inconsistent information
        if is_high_level and len(documents) > 0:
            # Add a note about potential inconsistency for the agent to be aware
            consistency_note = """
            Note: Information across different parts of the codebase may be inconsistent. 
            If you find conflicting information about services, microservices, or project structure,
            prioritize information from:
            1. The main README file
            2. Project overview documents
            3. The most recently updated files
            
            Synthesize information carefully and acknowledge any significant inconsistencies.
            When using information from secondary repositories, clearly indicate which repository it comes from.
            """
            
            # Add as a special document at the beginning
            meta = {"source": "system", "score": 1.0, "is_consistency_note": True}
            consistency_doc = Document(page_content=consistency_note, metadata=meta)
            documents.insert(0, consistency_doc)

        return documents

# --- Tool Definitions ---

def get_tools() -> List[Tool]:
    """Initializes and returns the list of tools available to the agent."""
    tools = []

    # 1. RAG Retriever Tool
    try:
        code_retriever = Neo4jCodeRetriever(k=10) # Using the increased k value
        rag_tool = Tool(
            name="CodeBaseRetriever",
            # Ensure the primary func used by the Tool is the async one if agent calls are async
            func=code_retriever.ainvoke, # Use async invoke
            description="Searches and retrieves relevant information from the indexed codebase based on semantic similarity to the query. ALWAYS use this tool FIRST for ANY question about the project, including high-level overviews, project purpose, architecture, features, and general information. This tool should be your primary source for understanding what the software project is about, how it's structured, and its main components. It's also useful for finding specific code examples, understanding functionality, and answering detailed technical questions.",
            coroutine=code_retriever.ainvoke # Explicitly specify coroutine for async use
        )
        tools.append(rag_tool)
        logger.info("CodeBaseRetriever tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize CodeBaseRetriever tool: {e}", exc_info=True)

    # 2. Project Overview Tool - Returns information about project structure
    try:
        # Updated wrapper to use graph-based queries with repository context
        async def get_project_overview(query: str = "", query_type: str = "overview", repository_url: str = None) -> str:
            """Get high-level information about the project structure and services directly from the knowledge graph.
            
            Args:
                query: The original query text for context
                query_type: Type of information to retrieve (overview, microservices, architecture, project_structure)
                repository_url: Optional URL of specific repository to query (defaults to active repo)
            """
            # Extract the topic based on the query or use the explicit query_type
            topic = query_type if query_type != "overview" else "overview"
            
            # Get active repository if none specified
            if not repository_url:
                active_repo = await db_manager.get_active_repository()
                if active_repo:
                    repository_url = active_repo.get('url')
                    logger.info(f"Using active repository for ProjectInfo: {repository_url}")
            
            # Override topic based on query content if query_type wasn't explicitly specified
            if query and query_type == "overview":
                if "microservice" in query.lower() or "service" in query.lower():
                    topic = "microservices"
                elif "architecture" in query.lower():
                    topic = "architecture"
                elif "structure" in query.lower() or "organization" in query.lower() or "layout" in query.lower():
                    topic = "project_structure"
                
            try:
                # Use specialized graph query with repository context
                results = await db_manager.query_high_level_info(topic, False, repository_url)
                
                if results and len(results) > 0:
                    # Format results based on topic
                    if topic == "project_structure":
                        # Organize by file path for project structure
                        paths_dict = {}
                        for r in results:
                            path = r.get("path", "unknown")
                            if path not in paths_dict:
                                paths_dict[path] = []
                            paths_dict[path].append(r.get("text", ""))
                        
                        repo_name = "Unknown"
                        if repository_url:
                            repo_name = repository_url.split('/')[-1].replace('.git', '')
                            
                        formatted = [f"## Project Structure Information for {repo_name}\n"]
                        
                        # Directory structure first (if present)
                        if 'directory_structure' in paths_dict:
                            formatted.append("### Directory Structure\n")
                            formatted.append("\n".join(paths_dict['directory_structure']))
                            formatted.append("\n")
                            # Remove to prevent duplication
                            del paths_dict['directory_structure']
                        
                        # Then README files
                        readme_paths = [p for p in paths_dict.keys() if 'README' in p]
                        if readme_paths:
                            formatted.append("### From README Files\n")
                            for path in readme_paths:
                                formatted.append(f"**File: {path}**\n")
                                formatted.append("\n".join(paths_dict[path]))
                                formatted.append("\n")
                                # Remove to prevent duplication
                                del paths_dict[path]
                        
                        # Then docs and other documentation
                        doc_paths = [p for p in paths_dict.keys() if '/docs/' in p or p.endswith('.md')]
                        if doc_paths:
                            formatted.append("### From Documentation\n")
                            for path in doc_paths:
                                formatted.append(f"**File: {path}**\n")
                                formatted.append("\n".join(paths_dict[path]))
                                formatted.append("\n")
                                # Remove to prevent duplication
                                del paths_dict[path]
                        
                        # Then everything else
                        if paths_dict:
                            formatted.append("### Additional Structure Information\n")
                            for path, texts in paths_dict.items():
                                formatted.append(f"**Source: {path}**\n")
                                formatted.append("\n".join(texts))
                                formatted.append("\n")
                            
                        return "\n".join(formatted)
                    else:
                        # Standard formatting for other topics
                        repo_name = "Unknown"
                        if repository_url:
                            repo_name = repository_url.split('/')[-1].replace('.git', '')
                            
                        combined_text = "\n\n".join([r.get("text", "") for r in results])
                        return f"Project information for {repo_name} gathered from the knowledge graph:\n\n{combined_text}"
                else:
                    # Provide a helpful message based on the topic
                    if topic == "project_structure":
                        return f"No project structure information found in the database for repository: {repository_url}. Try using the DirectoryExplorer tool, or the CodeBaseRetriever tool to search for README.md files."
                    elif topic == "microservices":
                        return f"No microservices information found for repository: {repository_url}. Try using the KnowledgeGraph tool with query_type='services'."
                    else:
                        return f"No specific project information found for repository: {repository_url}. Try using the CodeBaseRetriever tool to search for relevant documentation."
            except Exception as e:
                logger.error(f"Error in ProjectInfo tool: {e}", exc_info=True)
                return f"Error retrieving project information: {str(e)}. Please try the DirectoryExplorer or CodeBaseRetriever tool instead."
        
        project_info_tool = Tool(
            name="ProjectInfo",
            func=get_project_overview,
            description="Provides high-level information about the project structure, architecture, and services directly from the knowledge graph. Parameters: query (optional text query), query_type (optional - overview, microservices, architecture, project_structure)",
            coroutine=get_project_overview  # Mark as async
        )
        tools.append(project_info_tool)
        logger.info("ProjectInfo tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize ProjectInfo tool: {e}", exc_info=True)
        
    # Add a Knowledge Graph Query Tool
    try:
        async def query_knowledge_graph(query_type: str = "services", keywords: str = None) -> str:
            """
            Performs advanced knowledge graph queries that utilize graph relationships
            beyond simple vector similarity.
            
            Args:
                query_type: Type of query to perform (services, dependencies, structure, interface_analysis)
                keywords: Optional comma-separated keywords to filter results
            """
            try:
                # Parse keywords if provided
                keyword_list = None
                if keywords:
                    keyword_list = [k.strip() for k in keywords.split(',')]
                
                results = await db_manager.knowledge_graph_query(query_type, keyword_list)
                
                if not results or len(results) == 0:
                    return f"No results found for knowledge graph query of type '{query_type}'"
                
                # Format based on query type
                if query_type == "services":
                    formatted = ["## Services Identified in the Codebase\n"]
                    for item in results:
                        service_file = item.get("service_file", "")
                        functions = item.get("functions", [])
                        function_count = item.get("function_count", 0)
                        
                        # Format service name from path
                        service_name = service_file.split('/')[-1].replace('.', ' ').title() if '/' in service_file else service_file
                        
                        formatted.append(f"**Service**: {service_name}")
                        formatted.append(f"**File**: {service_file}")
                        formatted.append(f"**Function Count**: {function_count}")
                        if functions and len(functions) > 0:
                            top_functions = functions[:5] if len(functions) > 5 else functions
                            formatted.append(f"**Key Functions**: {', '.join(top_functions)}")
                        formatted.append("")
                
                elif query_type == "dependencies":
                    formatted = ["## Component Dependencies\n"]
                    for item in results:
                        source = item.get("source", "")
                        target = item.get("target", "")
                        strength = item.get("strength", 0)
                        
                        # Format component names
                        source_name = source.split('/')[-1] if '/' in source else source
                        target_name = target.split('/')[-1] if '/' in target else target
                        
                        formatted.append(f"**Dependency**: {source_name} → {target_name}")
                        formatted.append(f"**Strength**: {strength}")
                        formatted.append(f"**Source**: {source}")
                        formatted.append(f"**Target**: {target}")
                        formatted.append("")
                
                elif query_type == "structure":
                    formatted = ["## Repository Structure\n"]
                    for item in results:
                        repo = item.get("repository", "")
                        languages = item.get("language_breakdown", [])
                        total = item.get("total_files", 0)
                        
                        formatted.append(f"**Repository**: {repo}")
                        formatted.append(f"**Total Files**: {total}")
                        formatted.append("\n**Language Breakdown**:")
                        
                        # Sort languages by count
                        if languages:
                            # Format might vary, handle both object and dict formats
                            try:
                                # If it's a list of dicts
                                sorted_langs = sorted(languages, key=lambda x: x.get('count', 0), reverse=True)
                                for lang in sorted_langs[:10]:  # Show top 10
                                    language = lang.get('language', 'Unknown')
                                    count = lang.get('count', 0)
                                    percentage = (count / total) * 100 if total > 0 else 0
                                    formatted.append(f"- {language}: {count} files ({percentage:.1f}%)")
                            except Exception:
                                # Fallback format
                                formatted.append(f"- {str(languages)}")
                        
                        formatted.append("")
                
                else:
                    # Generic formatting for other query types
                    formatted = [f"## Knowledge Graph Results: {query_type}\n"]
                    for i, item in enumerate(results):
                        formatted.append(f"**Result {i+1}**:")
                        for key, value in item.items():
                            formatted.append(f"**{key}**: {value}")
                        formatted.append("")
                
                return "\n".join(formatted)
                
            except Exception as e:
                logger.error(f"Error in KnowledgeGraph tool: {e}", exc_info=True)
                return f"Error querying knowledge graph: {str(e)}"
        
        kg_tool = Tool(
            name="KnowledgeGraph",
            func=query_knowledge_graph,
            description="Performs advanced graph-based queries that analyze relationships between code components. This provides structural insights beyond text similarity. Parameters: query_type (services, dependencies, structure, interface_analysis), keywords (optional comma-separated filter terms)",
            coroutine=query_knowledge_graph
        )
        tools.append(kg_tool)
        logger.info("KnowledgeGraph tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize KnowledgeGraph tool: {e}", exc_info=True)
        
    # Add a direct Neo4j Query Tool
    try:
        async def direct_neo4j_query(query_type: str = "services") -> str:
            """
            Performs a direct Neo4j query to inspect database content.
            
            Args:
                query_type: Type of query to run (services, counts, structure, files, readme)
            """
            try:
                results = None
                
                if query_type == "services" or query_type == "microservices":
                    # Find information about services
                    results = await db_manager.raw_cypher_query("""
                    MATCH (cc:CodeChunk)
                    WHERE cc.text CONTAINS "service" 
                       OR cc.text CONTAINS "microservice"
                    RETURN cc.path AS path, substring(cc.text, 0, 300) AS preview
                    LIMIT 15
                    """)
                    if results:
                        formatted = ["## Services/Microservices Information in Database\n"]
                        for item in results:
                            formatted.append(f"**Path**: {item.get('path')}\n**Preview**: {item.get('preview')}...\n")
                        return "\n\n".join(formatted)
                        
                elif query_type == "counts":
                    # Get node counts by type
                    results = await db_manager.raw_cypher_query("""
                    MATCH (n)
                    RETURN labels(n) AS type, count(*) AS count
                    ORDER BY count DESC
                    """)
                    if results:
                        formatted = ["## Database Node Counts\n"]
                        for item in results:
                            formatted.append(f"**{item.get('type')}**: {item.get('count')} nodes")
                        return "\n\n".join(formatted)
                        
                elif query_type == "files":
                    # List files in the database
                    results = await db_manager.raw_cypher_query("""
                    MATCH (f:File)
                    RETURN f.path AS path, f.language AS language
                    LIMIT 20
                    """)
                    if results:
                        formatted = ["## Files in Database\n"]
                        for item in results:
                            formatted.append(f"**Path**: {item.get('path')}, **Language**: {item.get('language')}")
                        return "\n\n".join(formatted)
                
                elif query_type == "readme":
                    # Get README content
                    results = await db_manager.raw_cypher_query("""
                    MATCH (cc:CodeChunk)
                    WHERE cc.path CONTAINS 'README.md'
                    RETURN cc.path AS path, cc.text AS content
                    LIMIT 5
                    """)
                    if results:
                        formatted = ["## README Content in Database\n"]
                        for item in results:
                            formatted.append(f"**Path**: {item.get('path')}\n\n{item.get('content')}\n")
                        return "\n\n".join(formatted)
                
                elif query_type == "structure":
                    # Get repository structure
                    results = await db_manager.raw_cypher_query("""
                    MATCH (r:Repository)<-[:BELONGS_TO]-(f:File)
                    RETURN r.url AS repo, count(f) AS file_count,
                    collect(distinct f.language) AS languages
                    """)
                    if results:
                        formatted = ["## Repository Structure\n"]
                        for item in results:
                            formatted.append(f"**Repository**: {item.get('repo')}\n**File count**: {item.get('file_count')}\n**Languages**: {item.get('languages')}")
                            
                        # Add more detailed structure info
                        dir_results = await db_manager.raw_cypher_query("""
                        MATCH (f:File)
                        WITH split(f.path, '/') AS parts, count(*) AS count
                        WHERE size(parts) > 1
                        RETURN parts[0] AS top_dir, count
                        ORDER BY count DESC
                        LIMIT 10
                        """)
                        
                        if dir_results:
                            formatted.append("\n## Top-level Directories\n")
                            for item in dir_results:
                                formatted.append(f"**{item.get('top_dir')}**: {item.get('count')} files")
                                
                        return "\n\n".join(formatted)
                
                if not results:
                    return f"No data found for query type: {query_type}. Try a different query type: services, counts, structure, files, readme"
                    
                return "Query completed, but no results were formatted. Please check the logs."
                
            except Exception as e:
                logger.error(f"Error in DirectNeo4jQuery tool: {e}", exc_info=True)
                return f"Error querying Neo4j: {str(e)}"
        
        neo4j_tool = Tool(
            name="InspectDatabase",
            func=direct_neo4j_query,
            description="Directly queries the Neo4j database to inspect ingested content. Use this during testing to see what's actually in the database. Parameters: query_type (services, counts, structure, files, readme)",
            coroutine=direct_neo4j_query
        )
        tools.append(neo4j_tool)
        logger.info("InspectDatabase tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize InspectDatabase tool: {e}", exc_info=True)

    # 3. Web Search Tool (Tavily)
    if settings.tavily_api_key:
        try:
            # Pass the key explicitly to be safer if env var loading is suspect
            # tavily_tool = TavilySearchResults(max_results=3, tavily_api_key=settings.tavily_api_key)
            # Or rely on env var loading:
            tavily_tool = TavilySearchResults(max_results=3)
            tavily_tool.name = "WebSearch" # Give it a specific name
            tavily_tool.description = "Performs a web search using Tavily to find information about general programming concepts, external libraries, error messages, or recent developments not present in the indexed codebase. Use when the question seems to require up-to-date external knowledge or context."
            tools.append(tavily_tool)
            logger.info("WebSearch tool (Tavily) initialized.")
        except Exception as e:
            # Log the specific pydantic error if it occurs
            logger.error(f"Failed to initialize WebSearch tool (Tavily): {e}", exc_info=True)
            logger.warning("Proceeding without WebSearch tool. Ensure TAVILY_API_KEY is set in .env if needed.")
    else:
        logger.warning("TAVILY_API_KEY not found in environment config. WebSearch tool will not be available.")

    # Add a directory explorer tool for project structure
    try:
        async def explore_directories(repository_url: Optional[str] = None) -> str:
            """
            Provides a visual representation of the repository directory structure.
            
            Args:
                repository_url: Optional URL of the repository to analyze
            """
            try:
                # First get the active repository if none specified
                if not repository_url:
                    active_repo = await db_manager.get_active_repository()
                    if active_repo:
                        repository_url = active_repo.get('url')
                    
                if not repository_url:
                    return "No repository specified, and no active repository found."
                    
                # Get directory structure from the database
                query = """
                MATCH (r:Repository {url: $repo_url})<-[:BELONGS_TO]-(f:File)
                WITH f.path AS path
                RETURN path
                ORDER BY path
                """
                
                results = await db_manager.run_query(query, {"repo_url": repository_url})
                
                if not results or len(results) == 0:
                    return f"No files found for repository {repository_url}"
                    
                # Build directory tree structure
                dir_tree = {}
                for result in results:
                    path = result.get('path', '')
                    parts = path.split('/')
                    
                    # Skip empty paths
                    if not path or not parts:
                        continue
                        
                    # Build tree
                    current = dir_tree
                    for i, part in enumerate(parts):
                        if i == len(parts) - 1:  # File
                            if 'files' not in current:
                                current['files'] = []
                            current['files'].append(part)
                        else:  # Directory
                            if 'dirs' not in current:
                                current['dirs'] = {}
                            if part not in current['dirs']:
                                current['dirs'][part] = {}
                            current = current['dirs'][part]
                
                # Format output as markdown tree
                lines = [f"# Directory Structure for Repository: {repository_url.split('/')[-1]}\n"]
                
                def format_tree(node, prefix="", is_last=True, indent=""):
                    # Add directories
                    if 'dirs' in node:
                        dirs = list(node['dirs'].items())
                        for i, (name, subdir) in enumerate(dirs):
                            is_dir_last = i == len(dirs) - 1 and ('files' not in node or not node['files'])
                            lines.append(f"{indent}{prefix}📂 {name}/")
                            format_tree(
                                subdir,
                                prefix="└── " if is_dir_last else "├── ",
                                is_last=is_dir_last,
                                indent=indent + ("    " if is_last else "│   ")
                            )
                    
                    # Add files
                    if 'files' in node:
                        files = node['files']
                        for i, file in enumerate(files):
                            is_file_last = i == len(files) - 1
                            lines.append(f"{indent}{prefix}📄 {file}")
                
                format_tree(dir_tree)
                return "\n".join(lines)
                
            except Exception as e:
                logger.error(f"Error exploring directories: {e}", exc_info=True)
                return f"Error exploring directory structure: {str(e)}"

        directory_explorer_tool = Tool(
            name="DirectoryExplorer",
            func=explore_directories,
            description="Generates a visual representation of the repository directory structure. Use this when you need to understand the folder organization of a project.",
            coroutine=explore_directories
        )
        tools.append(directory_explorer_tool)
        logger.info("DirectoryExplorer tool initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize DirectoryExplorer tool: {e}", exc_info=True)
    
    return tools

# Instantiate tools once
available_tools = get_tools()