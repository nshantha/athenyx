import React, { ReactNode } from 'react';

interface MainContentProps {
  children: ReactNode;
  className?: string;
}

const MainContent: React.FC<MainContentProps> = ({ 
  children,
  className = ''
}) => {
  return (
    <main 
      className={`
        flex-1 overflow-y-auto
        bg-[#f8f5f0]
        p-6
        ${className}
      `}
    >
      {children}
    </main>
  );
};

export default MainContent;
