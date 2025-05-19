# app/api/repository.py
import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Dict, Any, Optional
import os
import asyncio
import urllib.parse

from app.schemas.models import RepositoryInfo, RepositoryList, RepositoryCreate, RepositoryResponse, RepositoryConnectionList, RepositoryConnectionDetail
from app.db.neo4j_manager import db_manager
from ingestion.main import run_enhanced_ingestion

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/repositories", response_model=RepositoryList)
async def get_repositories():
    """
    Get a list of all repositories in the knowledge graph.
    """
    try:
        # Connect to the database if not already connected
        await db_manager.connect()
        
        # Get all repositories
        repositories = await db_manager.get_all_repositories()
        
        # Get active repository
        active_repo = await db_manager.get_active_repository()
        
        # Convert to model format
        repo_list = [
            RepositoryInfo(
                url=repo.get('url', ''),
                service_name=repo.get('service_name', ''),
                description=repo.get('description', ''),
                last_commit=repo.get('last_commit', ''),
                last_indexed=repo.get('last_indexed', ''),
                is_active=(active_repo and repo.get('url') == active_repo.get('url', ''))
            )
            for repo in repositories
        ]
        
        # Return the list
        return RepositoryList(
            repositories=repo_list,
            active_repository=RepositoryInfo(**active_repo) if active_repo else None
        )
        
    except Exception as e:
        logger.error(f"Error retrieving repositories: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve repositories: {str(e)}"
        )

@router.post("/repositories", response_model=RepositoryResponse)
async def create_repository(repo: RepositoryCreate, background_tasks: BackgroundTasks):
    """
    Add a new repository to the knowledge graph and start ingestion.
    """
    try:
        # Connect to the database
        await db_manager.connect()
        
        # Create the repository node
        repo_url = repo.url
        service_name = repo_url.split('/')[-1].replace('.git', '')
        
        query = """
        MERGE (r:Repository {url: $url})
        SET r.service_name = $service_name,
            r.description = $description,
            r.last_updated = datetime(),
            r.last_commit_hash = $last_commit_hash
        RETURN r
        """
        params = {
            "url": repo_url,
            "service_name": service_name,
            "description": repo.description or "",
            "last_commit_hash": ""  # Initialize with empty string to avoid null property
        }
        
        await db_manager.run_query(query, params)
        logger.info(f"Created/updated Repository node for {repo_url}")
        
        # Set environment variables for ingestion
        os.environ["INGEST_REPO_URL"] = repo.url
        if repo.branch:
            os.environ["INGEST_REPO_BRANCH"] = repo.branch
            
        # Start ingestion in the background
        background_tasks.add_task(_run_ingestion)
        
        # Return success response
        return RepositoryResponse(
            success=True,
            message=f"Repository added and ingestion started: {repo.url}",
            repository=RepositoryInfo(
                url=repo.url,
                service_name=service_name,
                description=repo.description
            )
        )
        
    except Exception as e:
        logger.error(f"Error adding repository: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add repository: {str(e)}"
        )

@router.post("/repositories/{repo_url:path}/activate", response_model=RepositoryResponse)
async def set_active_repository(repo_url: str):
    """
    Set a repository as the active context for queries.
    """
    try:
        # Connect to the database if not already connected
        await db_manager.connect()
        
        # URL-decode the repository URL if needed
        decoded_url = urllib.parse.unquote(repo_url)
        logger.info(f"Setting active repository: {decoded_url}")
        
        # Set the active repository
        success = await db_manager.set_active_repository(decoded_url)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository not found: {decoded_url}"
            )
            
        # Get the repository info
        active_repo = await db_manager.get_active_repository()
        
        # Return success response
        return RepositoryResponse(
            success=True,
            message=f"Repository set as active: {decoded_url}",
            repository=RepositoryInfo(**active_repo) if active_repo else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting active repository: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set active repository: {str(e)}"
        )

def _run_ingestion():
    """Run ingestion in a synchronous context for background tasks."""
    try:
        # Run as a separate process to avoid asyncio event loop conflicts
        import subprocess
        import sys
        import threading
        
        # Use the same Python executable that's running this process
        python_executable = sys.executable
        
        # Prepare environment variables with the current environment
        env = os.environ.copy()
        
        # Ensure the repository URL is in the environment
        repo_url = env.get("INGEST_REPO_URL", "")
        if not repo_url:
            logger.error("No repository URL found in environment variables")
            return
            
        logger.info(f"Starting enhanced ingestion for repository: {repo_url}")
        
        # Run the ingestion directly with the main module, passing the repository URL as a command line argument
        cmd = [
            python_executable, 
            "-m", "ingestion.main",  # This runs the main() function
            "--repos", repo_url      # Explicitly pass the repo URL as a command line argument
        ]
        
        logger.info(f"Starting enhanced ingestion process: {' '.join(cmd)}")
        
        # Create a function to read and log output from the process
        def log_output(pipe, prefix):
            for line in iter(pipe.readline, b''):
                if line:
                    logger.info(f"{prefix}: {line.strip()}")
            
        # Start the process with the environment variables
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            universal_newlines=True,
            bufsize=1,
        )
        
        # Create threads to read and log the output
        stdout_thread = threading.Thread(target=log_output, args=(process.stdout, "INGESTION"))
        stderr_thread = threading.Thread(target=log_output, args=(process.stderr, "INGESTION ERROR"))
        
        # Set as daemon threads so they don't block process exit
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        
        # Start the threads
        stdout_thread.start()
        stderr_thread.start()
        
        logger.info("Enhanced ingestion process started with proper logging")
        
    except Exception as e:
        logger.error(f"Error during repository ingestion: {e}", exc_info=True)

@router.get("/repositories/{repo_url}/connections", response_model=RepositoryConnectionList)
async def get_repository_connections(repo_url: str):
    """
    Get connections between the specified repository and other repositories.
    """
    try:
        # URL decode the repository URL
        repo_url = urllib.parse.unquote(repo_url)
        
        # Connect to the database
        await db_manager.connect()
        
        # Get repository connections
        connections = await db_manager.get_repository_connections_summary(repo_url)
        
        # Return the connections
        return RepositoryConnectionList(
            repository_url=repo_url,
            connections=connections
        )
        
    except Exception as e:
        logger.error(f"Error retrieving repository connections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve repository connections: {str(e)}"
        )

@router.get("/repositories/{source_url}/connections/{target_url}", response_model=RepositoryConnectionDetail)
async def get_repository_connection_details(source_url: str, target_url: str):
    """
    Get detailed information about the connection between two repositories.
    """
    try:
        # URL decode the repository URLs
        source_url = urllib.parse.unquote(source_url)
        target_url = urllib.parse.unquote(target_url)
        
        # Connect to the database
        await db_manager.connect()
        
        # Get connection details
        details = await db_manager.get_repository_connection_details(source_url, target_url)
        
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No connection found between {source_url} and {target_url}"
            )
        
        # Return the details
        return RepositoryConnectionDetail(
            source_url=source_url,
            target_url=target_url,
            details=details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving repository connection details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve repository connection details: {str(e)}"
        )

@router.get("/connections", response_model=RepositoryConnectionList)
async def get_all_repository_connections():
    """
    Get all connections between repositories in the system.
    """
    try:
        # Connect to the database
        await db_manager.connect()
        
        # Get all repository connections
        connections = await db_manager.get_repository_connections_summary()
        
        # Return the connections
        return RepositoryConnectionList(
            connections=connections
        )
        
    except Exception as e:
        logger.error(f"Error retrieving all repository connections: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve repository connections: {str(e)}"
        ) 