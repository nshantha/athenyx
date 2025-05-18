import React, { ReactNode } from 'react';

interface StatusCardProps {
  title: string;
  children: ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  className?: string;
  icon?: ReactNode;
  borderPosition?: 'left' | 'top' | 'right' | 'bottom' | 'none';
}

const StatusCard: React.FC<StatusCardProps> = ({
  title,
  children,
  variant = 'default',
  className = '',
  icon,
  borderPosition = 'left'
}) => {
  // Define variant-specific styles
  const variantStyles = {
    default: {
      bg: 'bg-[#fffaf0]',
      border: 'border-[#e8e1d9]',
      title: 'text-[#3c3836]'
    },
    success: {
      bg: 'bg-green-50',
      border: 'border-green-500',
      title: 'text-green-700'
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-500',
      title: 'text-amber-700'
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-500',
      title: 'text-red-700'
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-500',
      title: 'text-blue-700'
    }
  };

  // Define border position styles
  const borderStyles = {
    left: `border-l-4 ${variantStyles[variant].border}`,
    top: `border-t-4 ${variantStyles[variant].border}`,
    right: `border-r-4 ${variantStyles[variant].border}`,
    bottom: `border-b-4 ${variantStyles[variant].border}`,
    none: ''
  };

  return (
    <div 
      className={`
        ${variantStyles[variant].bg} 
        ${borderPosition !== 'none' ? borderStyles[borderPosition] : ''}
        rounded-md shadow-sm p-4 border border-[#e8e1d9]
        ${className}
      `}
    >
      <div className="flex items-center gap-2 mb-2">
        {icon && <span>{icon}</span>}
        <h3 className={`font-semibold ${variantStyles[variant].title}`}>
          {title}
        </h3>
      </div>
      <div className="text-[#5d5a58]">
        {children}
      </div>
    </div>
  );
};

export default StatusCard;
