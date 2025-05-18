import React, { useEffect } from 'react';
import { useChat } from '../../hooks/useChat';
import { useRepositoryContext } from '../../context/RepositoryContext';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ExampleQuestions from './ExampleQuestions';
import StatusCard from '../ui/StatusCard';

interface ChatInterfaceProps {
  className?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ className = '' }) => {
  const { 
    messages, 
    isLoading, 
    error, 
    isChatReady, 
    activeRepository, 
    sendMessage 
  } = useChat();
  
  const { repositories } = useRepositoryContext();
  
  // Debug logging
  useEffect(() => {
    console.log('ChatInterface - Active repository:', activeRepository);
    console.log('ChatInterface - Is chat ready:', isChatReady);
    console.log('ChatInterface - Available repositories:', repositories);
  }, [activeRepository, isChatReady, repositories]);
  
  const handleSendMessage = async (message: string) => {
    console.log('ChatInterface - Sending message:', message);
    try {
      await sendMessage(message);
    } catch (error) {
      console.error('ChatInterface - Error sending message:', error);
    }
  };
  
  const handleSelectQuestion = async (question: string) => {
    console.log('ChatInterface - Example question selected:', question);
    try {
      await sendMessage(question);
    } catch (error) {
      console.error('ChatInterface - Error sending example question:', error);
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <div className="mb-6 text-[#3c3836] text-lg flex items-center">
        <span className="mr-2">💬</span>
        Ask questions about code, architecture, or functionality in natural language
      </div>
      
      {/* Repository Context */}
      {activeRepository && (
        <StatusCard
          title="Active Repository Context"
          variant="info"
          className="mb-6"
        >
          <div className="text-2xl font-bold mb-2">
            {activeRepository.service_name || activeRepository.name}
          </div>
          <div className="text-sm text-[#5d5a58] break-all">
            {activeRepository.url || activeRepository.path}
          </div>
        </StatusCard>
      )}
      
      {/* Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {messages.length > 0 ? (
          <MessageList messages={messages} isLoading={isLoading} />
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="bg-[#fffaf0] border border-[#e8e1d9] rounded-lg p-8 mb-8 shadow-sm">
              <h1 className="text-3xl font-bold text-[#2c6694] mb-4">
                Welcome to Actuamind 🧠
              </h1>
              <p className="text-[#3c3836] text-lg mb-8">
                Actuamind is an Enterprise AI Knowledge Platform that helps you understand and navigate complex codebases through a natural language interface.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-[#f8f5f0] border-l-4 border-[#2c6694] rounded-lg p-6">
                  <div className="text-3xl mb-4 text-[#2c6694]">🔍</div>
                  <h3 className="text-xl font-bold text-[#3c3836] mb-2">
                    Navigate Complex Codebases
                  </h3>
                  <p className="text-[#5d5a58]">
                    Ask questions about code structure, functionality, architecture, and specific implementations.
                  </p>
                </div>
                
                <div className="bg-[#f8f5f0] border-l-4 border-[#2c6694] rounded-lg p-6">
                  <div className="text-3xl mb-4 text-[#2c6694]">📊</div>
                  <h3 className="text-xl font-bold text-[#3c3836] mb-2">
                    Multi-Repository Support
                  </h3>
                  <p className="text-[#5d5a58]">
                    Index and query across multiple repositories with context switching.
                  </p>
                </div>
                
                <div className="bg-[#f8f5f0] border-l-4 border-[#2c6694] rounded-lg p-6">
                  <div className="text-3xl mb-4 text-[#2c6694]">🔄</div>
                  <h3 className="text-xl font-bold text-[#3c3836] mb-2">
                    Seamless Integration
                  </h3>
                  <p className="text-[#5d5a58]">
                    Add new repositories without interrupting your current work context.
                  </p>
                </div>
              </div>
              
              <ExampleQuestions onSelectQuestion={handleSelectQuestion} />
            </div>
          </div>
        )}
        
        {/* Chat Input */}
        <div className="mt-4">
          <ChatInput 
            onSendMessage={handleSendMessage} 
            disabled={!isChatReady || isLoading}
            isLoading={isLoading}
          />
          
          {!isChatReady && (
            <div className="mt-2 text-[#b45309] text-sm">
              Please select a repository from the sidebar to start chatting.
            </div>
          )}
          
          {error && (
            <div className="mt-2 text-[#b91c1c] text-sm">
              {error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
