# ingestion/sources/git_loader.py
import os
import shutil
import logging
import re
from git import Repo, GitCommandError, InvalidGitRepositoryError
from typing import List, Tuple, Optional

import git
from ingestion.config import ingestion_settings

logger = logging.getLogger(__name__)

class GitLoader:
    """
    Git repository loader for cloning and extracting repository content.
    """

    def __init__(self, repo_url: str, branch: str = None, clone_dir: str = None):
        """
        Initialize the GitLoader.
        
        Args:
            repo_url: URL of the Git repository
            branch: Branch to checkout (default: main branch)
            clone_dir: Directory to clone into (default: a temporary directory)
        """
        self.repo_url = repo_url
        self.branch = branch
        
        # Use ingestion_settings.clone_dir or passed clone_dir if specified
        if clone_dir:
            self.clone_dir = clone_dir
        else:
            self.clone_dir = ingestion_settings.clone_dir or os.path.join(
                ingestion_settings.base_clone_dir, 
                self.extract_repo_name(repo_url)
            )
            
        logger.info(f"GitLoader initialized with repo_url={repo_url}, branch={branch}, clone_dir={self.clone_dir}")
        self.repo = None
        
    def extract_repo_name(self, repo_url: str) -> str:
        """Extract the repository name from a URL."""
        # Remove trailing slashes and .git extension
        clean_url = repo_url.rstrip('/').rstrip('.git')
        
        # Get the last part of the URL (the repo name)
        parts = clean_url.split('/')
        repo_name = parts[-1]
        
        # Replace any problematic characters with underscores
        repo_name = repo_name.replace('.', '_').replace('-', '_')
        
        return repo_name
        
    def get_repo_and_commit(self) -> Tuple[git.Repo, str]:
        """
        Clone the repository (if needed) and get the current commit SHA.

        Returns:
            Tuple of (repo, commit_sha)
        """
        try:
            # Ensure the parent directory exists
            os.makedirs(os.path.dirname(self.clone_dir), exist_ok=True)
            
            if os.path.exists(os.path.join(self.clone_dir, '.git')):
                # Repository already exists, pull latest changes
                logger.info(f"Repository exists at {self.clone_dir}, pulling latest changes...")
                self.repo = git.Repo(self.clone_dir)
                # Ensure we're on the right branch if specified
                if self.branch:
                    current_branch = self.repo.active_branch.name
                    if current_branch != self.branch:
                        logger.info(f"Switching from {current_branch} to {self.branch}")
                        self.repo.git.checkout(self.branch)
                # Pull the latest changes
                self.repo.git.pull()
            else:
                # Clone the repository
                logger.info(f"Cloning repository {self.repo_url} to {self.clone_dir}...")
                if self.branch:
                    self.repo = git.Repo.clone_from(self.repo_url, self.clone_dir, branch=self.branch)
                else:
                    self.repo = git.Repo.clone_from(self.repo_url, self.clone_dir)

            # Get the commit SHA
            commit_sha = self.repo.head.commit.hexsha
            logger.info(f"Repository at commit {commit_sha}")
            
            return self.repo, commit_sha
            
        except git.GitCommandError as e:
            logger.error(f"Git command error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in get_repo_and_commit: {e}")
            raise

    def get_files_content(self, target_extensions: List[str]) -> List[Tuple[str, str]]:
        """Gets the content of files matching target extensions."""
        if not self.repo:
            raise ValueError("Repository not initialized. Call get_repo_and_commit first.")

        # Print target extensions for debugging
        logger.info(f"Looking for files with these extensions: {target_extensions}")

        files_content = []
        
        # Parse .gitignore if it exists
        ignored_patterns = []
        gitignore_path = os.path.join(self.clone_dir, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Convert gitignore pattern to regex pattern
                            pattern = line.replace('.', r'\.').replace('*', '.*')
                            ignored_patterns.append(re.compile(pattern))
            except Exception as e:
                logger.warning(f"Error parsing .gitignore: {e}")
        
        # Function to check if a file should be ignored
        def should_ignore(file_path):
            for pattern in ignored_patterns:
                if pattern.search(file_path):
                    return True
            return False
        
        # Walk through the repository directory
        for root, _, files in os.walk(self.clone_dir):
            # Skip .git directory
            if '.git' in root:
                continue
                
            for file in files:
                # Check if file has a target extension
                if any(file.endswith(ext) for ext in target_extensions):
                    file_path = os.path.join(root, file)
                    
                    # Get relative path from clone directory
                    rel_path = os.path.relpath(file_path, self.clone_dir)
                        
                    # Skip if file matches a gitignore pattern
                    if should_ignore(rel_path):
                        logger.debug(f"Skipping ignored file: {rel_path}")
                        continue
                            
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                            
                            # Add to files_content list
                            files_content.append((rel_path, content))
                            
                            # Log found files
                            if len(files_content) % 50 == 0:
                                logger.info(f"Found {len(files_content)} files so far...")
                                
                    except Exception as e:
                        logger.warning(f"Error reading file {rel_path}: {e}")
        
        logger.info(f"Found {len(files_content)} files with target extensions: {target_extensions}")
        return files_content