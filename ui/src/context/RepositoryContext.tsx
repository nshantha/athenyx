import React, { createContext, useState, useEffect, useContext, ReactNode, useRef } from 'react';
import { Repository } from '../types/repository';
import { getRepositories, getRepository } from '../services/repositoryService';

interface RepositoryContextType {
  repositories: Repository[];
  activeRepository: Repository | null;
  isLoading: boolean;
  error: string | null;
  setActiveRepository: (repo: Repository) => void;
  refreshRepositories: () => Promise<void>;
  setPollingEnabled: (enabled: boolean) => void;
}

const RepositoryContext = createContext<RepositoryContextType | undefined>(undefined);

// Polling interval in milliseconds (10 seconds)
const POLLING_INTERVAL = 10000;

export const RepositoryProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [activeRepository, setActiveRepository] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [pollingEnabled, setPollingEnabled] = useState<boolean>(false);
  
  // Use a ref to track the interval ID
  const pollingIntervalRef = useRef<number | null>(null);

  // Fetch repositories on component mount
  useEffect(() => {
    refreshRepositories();
    
    // Clean up interval on unmount
    return () => {
      if (pollingIntervalRef.current !== null) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  // Set up or tear down polling when pollingEnabled changes
  useEffect(() => {
    if (pollingEnabled) {
      // Start polling
      pollingIntervalRef.current = window.setInterval(() => {
        refreshRepositories();
      }, POLLING_INTERVAL);
      
      console.log('Repository status polling started');
    } else {
      // Stop polling
      if (pollingIntervalRef.current !== null) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
        console.log('Repository status polling stopped');
      }
    }
    
    // Clean up on unmount or when pollingEnabled changes
    return () => {
      if (pollingIntervalRef.current !== null) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [pollingEnabled]);

  // Function to refresh repositories list
  const refreshRepositories = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await getRepositories();
      setRepositories(response.repositories);
      
      // If there's an active repository, refresh its data
      if (activeRepository) {
        const updatedRepo = await getRepository(activeRepository.id);
        setActiveRepository(updatedRepo);
      }
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error fetching repositories:', error);
      setError('Failed to fetch repositories');
      setIsLoading(false);
    }
  };

  // Function to set active repository
  const handleSetActiveRepository = (repo: Repository) => {
    setActiveRepository(repo);
  };

  return (
    <RepositoryContext.Provider
      value={{
        repositories,
        activeRepository,
        isLoading,
        error,
        setActiveRepository: handleSetActiveRepository,
        refreshRepositories,
        setPollingEnabled
      }}
    >
      {children}
    </RepositoryContext.Provider>
  );
};

export const useRepositoryContext = (): RepositoryContextType => {
  const context = useContext(RepositoryContext);
  if (context === undefined) {
    throw new Error('useRepositoryContext must be used within a RepositoryProvider');
  }
  return context;
};
