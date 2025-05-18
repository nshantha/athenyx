import React from 'react';
import { useNavigate } from 'react-router-dom';

const Header: React.FC = () => {
  const navigate = useNavigate();

  const handleNavigation = (path: string, e: React.MouseEvent) => {
    e.preventDefault();
    navigate(path);
  };

  return (
    <header className="bg-white border-b border-[#e8e1d9] text-[#3c3836] p-4 shadow-sm">
      <div className="container mx-auto flex justify-between items-center">
        <div className="flex items-center">
          <h1 className="text-2xl font-bold text-[#2c6694]">
            <a 
              href="/" 
              onClick={(e) => handleNavigation('/', e)}
              className="transition-all duration-300 hover:opacity-80"
            >
              ActuaMind
            </a>
          </h1>
          <span className="ml-3 text-sm bg-[#f1ede7] text-[#5d5a58] px-3 py-1 rounded-full">Enterprise AI Knowledge Platform</span>
        </div>
        <nav>
          <ul className="flex space-x-6">
            <li>
              <a 
                href="/"
                onClick={(e) => handleNavigation('/', e)} 
                className="hover:text-[#3d85c6] transition-all duration-300 font-medium relative group"
              >
                Home
                <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-[#3d85c6] transition-all duration-300 group-hover:w-full"></span>
              </a>
            </li>
            <li>
              <a 
                href="/settings"
                onClick={(e) => handleNavigation('/settings', e)} 
                className="hover:text-[#3d85c6] transition-all duration-300 font-medium relative group"
              >
                Settings
                <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-[#3d85c6] transition-all duration-300 group-hover:w-full"></span>
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;
