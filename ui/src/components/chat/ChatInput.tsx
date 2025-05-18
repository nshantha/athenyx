import React, { useState, useRef, useEffect } from 'react';
import { validateChatMessage } from '../../utils/validators';

interface ChatInputProps {
  onSendMessage: (message: string) => Promise<void>;
  disabled?: boolean;
  isLoading?: boolean;
  className?: string;
}

interface ValidationState {
  valid: boolean;
  message: string;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled = false,
  isLoading = false,
  className = ''
}) => {
  const [message, setMessage] = useState('');
  const [validation, setValidation] = useState<ValidationState>({ valid: true, message: '' });
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [message]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Form submitted with message:', message);
    console.log('Is disabled:', disabled);
    console.log('Is loading:', isLoading);
    
    // Validate message
    const result = validateChatMessage(message);
    console.log('Validation result:', result);
    
    if (!result.valid) {
      setValidation({ valid: result.valid, message: result.message || 'Invalid message' });
      return;
    }
    
    // Reset validation
    setValidation({ valid: true, message: '' });
    
    // Send message and clear input
    console.log('Sending message to onSendMessage...');
    try {
      await onSendMessage(message);
      console.log('Message sent successfully');
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      console.log('Enter key pressed, submitting form');
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form 
      onSubmit={handleSubmit} 
      className={`relative ${className}`}
    >
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isLoading}
          placeholder={disabled 
            ? "Please select a repository first..." 
            : "Ask a question about the project..."}
          rows={1}
          className={`
            w-full px-4 py-3 pr-12
            bg-gray-800 border 
            ${!validation.valid ? 'border-red-500' : 'border-gray-700'} 
            rounded-lg resize-none
            text-gray-200 placeholder-gray-500
            focus:outline-none focus:ring-1 focus:ring-green-500
            disabled:bg-gray-900 disabled:cursor-not-allowed
          `}
        />
        
        <button
          type="submit"
          disabled={disabled || isLoading || !message.trim()}
          className={`
            absolute right-2 top-1/2 transform -translate-y-1/2
            p-2 rounded-full
            ${message.trim() && !disabled && !isLoading
              ? 'bg-green-600 hover:bg-green-700 text-white'
              : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            }
            transition-colors
          `}
          onClick={(e) => {
            console.log('Send button clicked');
            handleSubmit(e);
          }}
        >
          {isLoading ? (
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          )}
        </button>
      </div>
      
      {!validation.valid && (
        <p className="mt-1 text-sm text-red-500">{validation.message}</p>
      )}
      
      <p className="mt-1 text-xs text-gray-500">
        Press Enter to send, Shift+Enter for new line
      </p>
    </form>
  );
};

export default ChatInput;
