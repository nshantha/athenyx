import React, { useEffect } from 'react';
import { useRepositories } from '../../hooks/useRepositories';
import { useRepositoryContext } from '../../context/RepositoryContext';
import { Repository, RepositoryStatus } from '../../types/repository';

interface IngestionStatusProps {
  className?: string;
}

const IngestionStatus: React.FC<IngestionStatusProps> = ({ className = '' }) => {
  const { repositories, setPollingEnabled } = useRepositoryContext();
  
  // Find repositories that are currently being ingested
  const ingestingRepositories = repositories.filter(
    repo => repo.status === RepositoryStatus.PENDING || repo.status === RepositoryStatus.PROCESSING
  );
  
  // Enable polling if there are repositories being ingested
  useEffect(() => {
    const hasIngestingRepos = ingestingRepositories.length > 0;
    setPollingEnabled(hasIngestingRepos);
    
    return () => {
      // Disable polling when component unmounts
      setPollingEnabled(false);
    };
  }, [ingestingRepositories.length, setPollingEnabled]);
  
  if (ingestingRepositories.length === 0) {
    return null;
  }
  
  return (
    <div className={`mt-4 p-4 bg-yellow-900/20 border border-yellow-800 rounded-md ${className}`}>
      <h3 className="text-yellow-500 font-bold mb-2">Repository Ingestion Status</h3>
      
      <div className="space-y-3">
        {ingestingRepositories.map(repo => (
          <RepositoryIngestionItem key={repo.id} repository={repo} />
        ))}
      </div>
      
      <div className="mt-3 text-xs text-gray-400">
        Status updates automatically every 10 seconds
      </div>
    </div>
  );
};

// Component to display individual repository ingestion status
const RepositoryIngestionItem = ({ repository }: { repository: Repository }) => {
  const getProgressValue = () => {
    switch (repository.status) {
      case RepositoryStatus.PENDING:
        return 10;
      case RepositoryStatus.PROCESSING:
        return 50;
      case RepositoryStatus.COMPLETED:
        return 100;
      default:
        return 0;
    }
  };
  
  const getStatusText = () => {
    switch (repository.status) {
      case RepositoryStatus.PENDING:
        return 'Pending';
      case RepositoryStatus.PROCESSING:
        return 'Processing';
      case RepositoryStatus.COMPLETED:
        return 'Completed';
      case RepositoryStatus.FAILED:
        return 'Failed';
      default:
        return 'Unknown';
    }
  };
  
  const progress = getProgressValue();
  
  return (
    <div className="bg-gray-800/50 p-3 rounded-md">
      <div className="flex justify-between mb-1">
        <span className="font-medium text-white">
          {repository.service_name || repository.name}
        </span>
        <span className="text-yellow-500">{getStatusText()}</span>
      </div>
      
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <div 
          className="bg-yellow-500 h-2.5 rounded-full transition-all duration-500" 
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      
      <div className="mt-1 text-xs text-gray-400">
        {repository.status === RepositoryStatus.COMPLETED 
          ? 'Ingestion complete' 
          : 'Ingestion in progress...'}
      </div>
    </div>
  );
};

export default IngestionStatus;
