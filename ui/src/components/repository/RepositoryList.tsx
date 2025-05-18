import React from 'react';
import { Repository } from '../../types/repository';
import RepositoryCard from './RepositoryCard';

interface RepositoryListProps {
  repositories: Repository[];
  activeRepository: Repository | null;
  loading: boolean;
}

const RepositoryList: React.FC<RepositoryListProps> = ({
  repositories,
  activeRepository,
  loading
}) => {
  if (loading) {
    return (
      <div className="py-4">
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-gray-700 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-700 rounded"></div>
              <div className="h-4 bg-gray-700 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (repositories.length === 0) {
    return (
      <div className="py-4">
        <div className="bg-yellow-900/20 border border-yellow-800 text-yellow-200 p-3 rounded">
          No repositories found. Add your first repository below.
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="font-bold text-green-500 mb-2">Select Repository</h3>
      <div className="space-y-2">
        {repositories.map((repo) => (
          <RepositoryCard
            key={repo.id}
            repository={repo}
            isActive={activeRepository?.id === repo.id}
          />
        ))}
      </div>
    </div>
  );
};

export default RepositoryList;
