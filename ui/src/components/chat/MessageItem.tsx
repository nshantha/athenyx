import React from 'react';
import { Message } from '../../types/chat';
import { formatMarkdown } from '../../utils/formatters';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MessageItemProps {
  message: Message;
  isLoading?: boolean;
  className?: string;
}

const MessageItem: React.FC<MessageItemProps> = ({
  message,
  isLoading = false,
  className = ''
}) => {
  const isUser = message.role === 'user';
  const formattedContent = formatMarkdown(message.content);
  
  return (
    <div 
      className={`
        flex items-start
        ${isUser ? 'justify-end' : 'justify-start'}
        ${className}
      `}
    >
      {/* Avatar */}
      <div 
        className={`
          flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
          ${isUser ? 'order-2 ml-3 bg-green-600' : 'order-1 mr-3 bg-blue-600'}
        `}
      >
        {isUser ? '👤' : '🤖'}
      </div>
      
      {/* Message Content */}
      <div 
        className={`
          max-w-3xl rounded-lg p-4
          ${isUser 
            ? 'order-1 bg-green-900/30 border border-green-800' 
            : 'order-2 bg-gray-800 border border-gray-700'
          }
        `}
      >
        <ReactMarkdown
          components={{
            // @ts-ignore - Ignoring type issues with ReactMarkdown components
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter
                  // @ts-ignore - Ignoring type issues with SyntaxHighlighter style
                  style={vscDarkPlus}
                  language={match[1]}
                  PreTag="div"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={`bg-gray-900 px-1 py-0.5 rounded text-gray-200 ${className}`} {...props}>
                  {children}
                </code>
              );
            }
          }}
        >
          {formattedContent}
        </ReactMarkdown>
        
        {isLoading && (
          <div className="mt-2 text-gray-400">
            <span className="inline-block animate-pulse">▌</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageItem;
