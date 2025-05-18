/**
 * Validate a repository URL
 */
export const validateRepositoryUrl = (url: string): { valid: boolean; message?: string } => {
  if (!url || url.trim() === '') {
    return { valid: false, message: 'Repository URL cannot be empty' };
  }

  // Check if URL is a valid Git URL
  const gitUrlPattern = /^(https?:\/\/|git@)([a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]+(\/|:)[a-zA-Z0-9-]+\/[a-zA-Z0-9-]+(\.git)?$/;
  
  if (!gitUrlPattern.test(url)) {
    return { 
      valid: false, 
      message: 'Invalid Git URL format. Example: https://github.com/username/repository.git' 
    };
  }

  return { valid: true };
};

/**
 * Validate a chat message
 */
export const validateChatMessage = (message: string): { valid: boolean; message?: string } => {
  if (!message || message.trim() === '') {
    return { valid: false, message: 'Message cannot be empty' };
  }

  if (message.length > 1000) {
    return { valid: false, message: 'Message is too long (max 1000 characters)' };
  }

  return { valid: true };
};
