import React, { ReactNode, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';

interface LayoutProps {
  children: ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayContent, setDisplayContent] = useState<ReactNode>(children);
  const [prevPathname, setPrevPathname] = useState(location.pathname);

  // Handle content updates without transitions for initial load
  useEffect(() => {
    setDisplayContent(children);
  }, []);

  // Handle transitions between routes
  useEffect(() => {
    // Only trigger transition if the pathname has changed
    if (prevPathname !== location.pathname) {
      // Start transition
      setIsTransitioning(true);
      
      // After fade out completes, update content
      const timer = setTimeout(() => {
        setDisplayContent(children);
        setIsTransitioning(false);
        setPrevPathname(location.pathname);
      }, 200);
      
      return () => clearTimeout(timer);
    } else {
      // If it's the same route but with different state/params, just update content
      setDisplayContent(children);
    }
  }, [children, location.pathname, prevPathname]);

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className={`
          flex-1 p-4 overflow-auto
          transition-opacity duration-200 ease-in-out
          ${isTransitioning ? 'opacity-0' : 'opacity-100'}
        `}>
          {displayContent}
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default Layout; 