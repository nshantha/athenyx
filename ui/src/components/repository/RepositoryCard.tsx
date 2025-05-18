import React from 'react';
import { Repository } from '../../types/repository';
import { useRepositories } from '../../hooks/useRepositories';
import { formatDate } from '../../utils/formatters';

interface RepositoryCardProps {
  repository: Repository;
  isActive: boolean;
  className?: string;
}

const RepositoryCard: React.FC<RepositoryCardProps> = ({
  repository,
  isActive,
  className = ''
}) => {
  const { setActiveRepository } = useRepositories();
  
  const handleActivate = async () => {
    if (!isActive) {
      setActiveRepository(repository);
    }
  };
  
  const lastIndexed = repository.last_indexed
    ? formatDate(repository.last_indexed)
    : 'Not indexed yet';
    
  const statusText = repository.last_indexed
    ? `Indexed: ${lastIndexed}`
    : lastIndexed;

  return (
    <div 
      className={`
        ${isActive 
          ? 'bg-green-900/20 border-green-500' 
          : 'bg-blue-900/10 border-blue-800 hover:bg-blue-900/20'
        }
        border rounded p-3 cursor-pointer transition-colors
        ${className}
      `}
      onClick={handleActivate}
    >
      <div className="font-bold text-white">
        {repository.service_name || repository.name}
      </div>
      
      <div className="text-xs text-gray-400">
        {statusText}
      </div>
      
      {!isActive && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleActivate();
          }}
          className="mt-2 text-sm bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded transition-colors"
        >
          Set as Active
        </button>
      )}
    </div>
  );
};

export default RepositoryCard;
