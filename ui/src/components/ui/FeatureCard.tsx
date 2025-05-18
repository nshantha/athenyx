import React, { ReactNode } from 'react';

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  className?: string;
  accentColor?: string;
}

const FeatureCard: React.FC<FeatureCardProps> = ({
  icon,
  title,
  description,
  className = '',
  accentColor = 'border-green-500'
}) => {
  return (
    <div 
      className={`
        bg-gray-800/60 
        border-l-4 ${accentColor}
        rounded-lg p-6 h-full
        transition-transform duration-300 hover:-translate-y-1
        ${className}
      `}
    >
      <div className={`text-3xl mb-4 ${accentColor.replace('border', 'text')}`}>
        {icon}
      </div>
      
      <h3 className="text-xl font-bold text-white mb-2">
        {title}
      </h3>
      
      <p className="text-gray-300">
        {description}
      </p>
    </div>
  );
};

export default FeatureCard;
