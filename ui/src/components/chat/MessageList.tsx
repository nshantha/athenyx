import React, { useRef, useEffect } from 'react';
import { Message } from '../../types/chat';
import MessageItem from './MessageItem';

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  className?: string;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = ''
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className={`flex-1 overflow-y-auto ${className}`}>
      <div className="space-y-6 pb-4">
        {messages.map((message, index) => (
          <MessageItem
            key={index}
            message={message}
            isLoading={isLoading && index === messages.length - 1 && message.role === 'assistant'}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
};

export default MessageList;
