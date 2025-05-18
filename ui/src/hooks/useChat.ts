import { useCallback } from 'react';
import { useChatContext } from '../context/ChatContext';
import { useRepositoryContext } from '../context/RepositoryContext';

export const useChat = () => {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    addContextSwitchMessage
  } = useChatContext();

  const { activeRepository } = useRepositoryContext();

  // Function to handle sending a message
  const handleSendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    
    await sendMessage(content);
  }, [sendMessage]);

  // Function to handle repository context switch
  const handleRepositorySwitch = useCallback((repoName: string) => {
    addContextSwitchMessage(repoName);
  }, [addContextSwitchMessage]);

  // Check if chat is ready (has active repository)
  const isChatReady = !!activeRepository;

  return {
    messages,
    isLoading,
    error,
    isChatReady,
    activeRepository,
    sendMessage: handleSendMessage,
    clearMessages,
    handleRepositorySwitch
  };
};
