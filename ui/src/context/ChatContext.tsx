import React, { createContext, useState, useContext, ReactNode } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { Message, MessageRole } from '../types/chat';
import { sendMessage } from '../services/chatService';
import { useRepositoryContext } from './RepositoryContext';

interface ChatContextType {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
  addContextSwitchMessage: (repoName: string) => void;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

const initialChatState: ChatState = {
  messages: [],
  isLoading: false,
  error: null
};

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [chatState, setChatState] = useState<ChatState>(initialChatState);
  const { activeRepository } = useRepositoryContext();

  // Clear all messages
  const clearMessages = () => {
    setChatState(initialChatState);
  };

  // Send a message to the API
  const sendChatMessage = async (content: string) => {
    console.log('sendChatMessage called with content:', content);
    console.log('Active repository:', activeRepository);
    
    if (!activeRepository) {
      console.error('No active repository selected');
      setChatState((prev: ChatState) => ({
        ...prev,
        error: 'No active repository selected'
      }));
      return;
    }

    // Add user message to state
    const userMessage: Message = { 
      id: uuidv4(),
      role: MessageRole.USER, 
      content,
      timestamp: new Date().toISOString()
    };
    
    console.log('Adding user message to state:', userMessage);
    setChatState((prev: ChatState) => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null
    }));

    let fullResponse = '';

    try {
      // Prepare request payload
      const payload = {
        repository_id: activeRepository.id,
        message: content
      };
      
      console.log('Sending message to API with payload:', payload);

      // Send message to API
      const response = await sendMessage(payload);
      console.log('Received response from API:', response);
      
      // Update state with the response
      setChatState((prev: ChatState) => ({
        ...prev,
        messages: [
          ...prev.messages,
          response.message
        ],
        isLoading: false
      }));
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage = 'Failed to send message. Please try again.';
      
      // Add error message
      setChatState((prev: ChatState) => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
    }
  };

  // Function to add context switch message
  const addContextSwitchMessage = (repoName: string) => {
    setChatState((prev: ChatState) => ({
      ...prev,
      messages: [
        ...prev.messages,
        {
          id: uuidv4(),
          role: MessageRole.SYSTEM,
          content: `Switched to repository: ${repoName}`,
          timestamp: new Date().toISOString()
        }
      ]
    }));
  };

  return (
    <ChatContext.Provider
      value={{
        messages: chatState.messages,
        isLoading: chatState.isLoading,
        error: chatState.error,
        sendMessage: sendChatMessage,
        clearMessages,
        addContextSwitchMessage
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChatContext = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
};
