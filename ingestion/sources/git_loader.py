# ingestion/sources/git_loader.py
import os
import shutil
import logging
import re
from git import Repo, GitCommandError, InvalidGitRepositoryError
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

class GitLoader:
    def __init__(self, repo_url: str, clone_dir: str, branch: Optional[str] = None):
        self.repo_url = repo_url
        
        # Use repository-specific clone directory if clone_dir is a base directory
        if os.path.basename(clone_dir) in ["cloned_repo", "repos"]:
            repo_name = self._extract_repo_name(repo_url)
            self.clone_dir = os.path.join(os.path.dirname(clone_dir), "repos", repo_name)
            logger.info(f"Using repository-specific clone directory: {self.clone_dir}")
        else:
            self.clone_dir = clone_dir
            
        self.branch = branch
        self.repo: Optional[Repo] = None

    @staticmethod
    def _extract_repo_name(repo_url: str) -> str:
        """Extract repository name from URL."""
        # Handle different URL formats
        # Example: https://github.com/org/repo.git or git@github.com:org/repo.git
        match = re.search(r'[:/]([^/]+/[^/]+?)(?:\.git)?$', repo_url)
        if match:
            # Replace any remaining slashes with underscores for a valid directory name
            repo_name = match.group(1).replace('/', '_')
            return repo_name
        return "unknown_repo"

    def _ensure_repo_cloned_or_updated(self) -> Repo:
        """Clones the repo if not present, or opens and pulls updates if it exists."""
        try:
            # Make sure parent directory exists
            os.makedirs(os.path.dirname(self.clone_dir), exist_ok=True)
            
            if os.path.exists(self.clone_dir):
                logger.info(f"Repository directory already exists at {self.clone_dir}. Opening.")
                try:
                    repo = Repo(self.clone_dir)
                    # Check if the existing repo URL matches
                    if repo.remotes.origin.url != self.repo_url:
                        logger.warning(f"Existing repo URL '{repo.remotes.origin.url}' differs from requested '{self.repo_url}'. Re-cloning.")
                        shutil.rmtree(self.clone_dir)
                        return self._clone_repo()

                    logger.info("Fetching updates from origin...")
                    repo.remotes.origin.fetch()
                    current_branch_or_commit = repo.head.commit
                    target_ref = f"origin/{self.branch}" if self.branch else "origin/HEAD" # Default branch might not be 'master' or 'main'

                    # Get the commit object for the target branch/ref on the remote
                    remote_commit = repo.commit(target_ref)

                    if current_branch_or_commit != remote_commit:
                       logger.info(f"Local commit {current_branch_or_commit} differs from remote {target_ref} ({remote_commit}). Pulling changes.")
                       # Ensure we are on the correct branch if specified
                       if self.branch:
                           repo.git.checkout(self.branch)
                       repo.remotes.origin.pull()
                       logger.info("Pull complete.")
                    else:
                        logger.info("Repository is up-to-date.")
                    return repo

                except InvalidGitRepositoryError:
                    logger.warning(f"{self.clone_dir} exists but is not a valid Git repository. Re-cloning.")
                    shutil.rmtree(self.clone_dir)
                    return self._clone_repo()
                except GitCommandError as e:
                    logger.error(f"Git command failed during update: {e}", exc_info=True)
                    raise # Re-raise critical errors
            else:
                return self._clone_repo()

        except Exception as e:
            logger.error(f"Failed to ensure repository presence/update: {e}", exc_info=True)
            raise

    def _clone_repo(self) -> Repo:
        """Clones the repository."""
        logger.info(f"Cloning repository from {self.repo_url} to {self.clone_dir}...")
        try:
            clone_args = {}
            if self.branch:
                clone_args['branch'] = self.branch
                logger.info(f"Cloning specific branch: {self.branch}")

            repo = Repo.clone_from(self.repo_url, self.clone_dir, **clone_args)
            logger.info("Repository cloned successfully.")
            return repo
        except GitCommandError as e:
            logger.error(f"Failed to clone repository: {e}", exc_info=True)
            raise

    def get_repo_and_commit(self) -> Tuple[Repo, str]:
        """Ensures the repo is ready and returns the Repo object and current commit SHA."""
        self.repo = self._ensure_repo_cloned_or_updated()
        commit_sha = self.repo.head.commit.hexsha
        logger.info(f"Current commit SHA: {commit_sha}")
        return self.repo, commit_sha

    def get_files_content(self, target_extensions: List[str]) -> List[Tuple[str, str]]:
        """Gets the content of files matching target extensions."""
        if not self.repo:
            raise ValueError("Repository not initialized. Call get_repo_and_commit first.")

        files_content = []
        for item in self.repo.tree().traverse():
            if item.type == 'blob': # 'blob' means file
                file_path = item.path
                _, ext = os.path.splitext(file_path)
                if ext in target_extensions:
                    try:
                        # Use item.data_stream which reads binary, decode carefully
                        content_bytes = item.data_stream.read()
                        content_text = content_bytes.decode('utf-8', errors='replace') # Replace errors
                        # Create a relative path suitable for storage/display
                        relative_path = file_path
                        files_content.append((relative_path, content_text))
                        logger.debug(f"Read file: {relative_path}")
                    except Exception as e:
                        logger.warning(f"Could not read or decode file {file_path}: {e}")
        logger.info(f"Found {len(files_content)} files matching extensions: {target_extensions}")
        return files_content