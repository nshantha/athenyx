import React, { useState } from 'react';
import { useRepositoryContext } from '../../context/RepositoryContext';
import { useNavigate } from 'react-router-dom';

const Sidebar: React.FC = () => {
  const { repositories, activeRepository, setActiveRepository } = useRepositoryContext();
  const [isOpen, setIsOpen] = useState(true);
  const navigate = useNavigate();

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  const handleAddRepository = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate('/settings');
  };

  return (
    <>
      <button 
        className="md:hidden fixed top-16 left-0 z-10 bg-[#2c6694] text-white p-2 rounded-r-md"
        onClick={toggleSidebar}
      >
        {isOpen ? '←' : '→'}
      </button>
      
      <aside className={`
        bg-[#fffaf0] w-64 shadow-sm border-r border-[#e8e1d9] transition-all duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0
        fixed md:relative h-full z-10
      `}>
        <div className="p-4 border-b border-[#e8e1d9] flex justify-between items-center">
          <h2 className="text-lg font-semibold text-[#3c3836]">Repositories</h2>
          <a 
            href="/settings"
            onClick={handleAddRepository}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-[#2c6694] text-white hover:bg-[#3d85c6] transition-all duration-300 transform hover:scale-110"
            title="Add Repository"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </a>
        </div>
        
        <div className="overflow-y-auto h-[calc(100%-60px)]">
          <ul className="p-2">
            {repositories.length === 0 ? (
              <li className="p-4 text-[#5d5a58] text-center">
                <p className="mb-2">No repositories found</p>
                <a 
                  href="/settings"
                  onClick={handleAddRepository}
                  className="inline-block px-3 py-2 bg-[#2c6694] text-white rounded hover:bg-[#3d85c6] transition-all duration-300 transform hover:scale-105 text-sm"
                >
                  Add Your First Repository
                </a>
              </li>
            ) : (
              repositories.map(repo => (
                <li 
                  key={repo.id}
                  className={`
                    p-3 mb-2 rounded cursor-pointer transition-all duration-200
                    ${activeRepository?.id === repo.id 
                      ? 'bg-[#e8e1d9] text-[#2c6694] border-l-4 border-[#2c6694]' 
                      : 'hover:bg-[#f1ede7] border-l-4 border-transparent hover:border-[#3d85c6]'}
                  `}
                  onClick={() => setActiveRepository(repo)}
                >
                  <div className="font-medium truncate">{repo.name}</div>
                  {repo.description && (
                    <div className="text-xs text-[#5d5a58] truncate mt-1">{repo.description}</div>
                  )}
                </li>
              ))
            )}
          </ul>
        </div>
      </aside>
      
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black bg-opacity-30 z-0"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  );
};

export default Sidebar;
