import { useState, useCallback } from 'react';
import { useRepositoryContext } from '../context/RepositoryContext';
import { createRepository, getRepositoryStatus } from '../services/repositoryService';
import { Repository } from '../types/repository';

export const useRepositories = () => {
  const {
    repositories,
    activeRepository,
    isLoading,
    error,
    refreshRepositories,
    setActiveRepository
  } = useRepositoryContext();

  const [addRepoStatus, setAddRepoStatus] = useState<{
    loading: boolean;
    error: string | null;
    success: boolean;
  }>({
    loading: false,
    error: null,
    success: false
  });

  // Function to add a new repository
  const handleAddRepository = useCallback(async (
    url: string, 
    branch?: string,
    description?: string
  ): Promise<boolean> => {
    setAddRepoStatus({ loading: true, error: null, success: false });
    
    try {
      // Add the repository
      await createRepository({ url, branch, description });
      
      setAddRepoStatus({ loading: false, error: null, success: true });
      
      // Refresh repositories list
      await refreshRepositories();
      
      return true;
    } catch (err: any) {
      setAddRepoStatus({ 
        loading: false, 
        error: err.message || 'Failed to add repository', 
        success: false 
      });
      return false;
    }
  }, [refreshRepositories]);

  // Function to check repository status
  const checkRepositoryStatusById = useCallback(async (id: string) => {
    try {
      const status = await getRepositoryStatus(id);
      return status;
    } catch (err) {
      console.error('Error checking repository status:', err);
      return null;
    }
  }, []);

  return {
    repositories,
    activeRepository,
    loading: isLoading,
    error,
    addRepoStatus,
    fetchRepositories: refreshRepositories,
    setActiveRepository,
    addRepository: handleAddRepository,
    checkRepositoryStatus: checkRepositoryStatusById
  };
};
