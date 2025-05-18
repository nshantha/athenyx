import { format, formatDistanceToNow } from 'date-fns';

/**
 * Format a date string to a readable format
 */
export const formatDate = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return format(date, 'MMM d, yyyy h:mm a');
  } catch (error) {
    return dateString;
  }
};

/**
 * Format elapsed time from a date string
 */
export const formatElapsedTime = (dateString: string): string => {
  try {
    const date = new Date(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    return 'unknown time';
  }
};

/**
 * Format a repository URL to a more readable form
 */
export const formatRepositoryUrl = (url: string): string => {
  try {
    // Remove protocol and trailing .git
    return url
      .replace(/^(https?:\/\/)/, '')
      .replace(/\.git$/, '')
      .replace(/\/$/, '');
  } catch (error) {
    return url;
  }
};

/**
 * Format markdown code blocks for proper display
 */
export const formatMarkdown = (text: string): string => {
  if (!text) return '';
  
  // Clean up the text
  const cleaned = text.trim();
  
  // Ensure code blocks are properly formatted
  return cleaned
    .replace(/```(\w+)\s+/g, '```$1\n')  // Fix language markers
    .replace(/\n\s*```/g, '\n```');      // Fix closing code blocks
};
