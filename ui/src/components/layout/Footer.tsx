import React from 'react';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-800 text-white p-4 text-center">
      <div className="container mx-auto">
        <p>&copy; {new Date().getFullYear()} ActuaMind - Enterprise AI Knowledge Platform</p>
        <p className="text-sm text-gray-400 mt-1">
          Powered by React, TypeScript, and AI
        </p>
      </div>
    </footer>
  );
};

export default Footer;
