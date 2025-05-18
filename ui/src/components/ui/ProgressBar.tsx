import React from 'react';

interface ProgressBarProps {
  value: number;
  max: number;
  className?: string;
  variant?: 'default' | 'warning' | 'success';
  showValue?: boolean;
  height?: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  max = 100,
  className = '',
  variant = 'default',
  showValue = false,
  height = '20px'
}) => {
  // Calculate percentage
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));
  
  // Determine color based on variant
  let bgColor = 'bg-blue-500';
  let trackColor = 'bg-blue-100 dark:bg-gray-700';
  
  if (variant === 'warning') {
    bgColor = 'bg-amber-500';
    trackColor = 'bg-amber-100 dark:bg-gray-700';
  } else if (variant === 'success') {
    bgColor = 'bg-green-500';
    trackColor = 'bg-green-100 dark:bg-gray-700';
  }

  return (
    <div className={`w-full ${className}`}>
      <div 
        className={`w-full rounded-full ${trackColor}`}
        style={{ height }}
      >
        <div
          className={`${bgColor} h-full rounded-full transition-all duration-300 ease-in-out`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 text-right">
          {Math.round(percentage)}%
        </div>
      )}
    </div>
  );
};

export default ProgressBar;
