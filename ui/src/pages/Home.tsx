import React from 'react';
import { useRepositories } from '../hooks/useRepositories';
import { useChat } from '../hooks/useChat';
import { useNavigate } from 'react-router-dom';
import IngestionStatus from '../components/repository/IngestionStatus';

// Helper components
const FeatureCard: React.FC<{ title: string; description: string; icon: string }> = ({ 
  title, 
  description, 
  icon 
}) => (
  <div className="bg-[#fffaf0] p-6 rounded-lg shadow-sm border border-[#e8e1d9] hover:shadow transition-shadow">
    <div className="text-3xl mb-4">{icon}</div>
    <h2 className="text-xl font-semibold mb-2 text-[#3c3836]">{title}</h2>
    <p className="text-[#5d5a58]">{description}</p>
  </div>
);

const ExampleQuestion: React.FC<{ text: string; onClick?: () => void }> = ({ text, onClick }) => (
  <button 
    onClick={onClick}
    className="text-left p-3 bg-[#f1ede7] hover:bg-[#e8e1d9] rounded-lg transition-colors w-full text-[#3c3836]"
  >
    {text}
  </button>
);

// Demo chat preview component
const ChatPreview: React.FC = () => (
  <div className="border border-[#e8e1d9] rounded-lg overflow-hidden bg-white shadow-sm mb-6">
    <div className="bg-[#f8f5f0] border-b border-[#e8e1d9] px-4 py-3 flex items-center">
      <div className="w-3 h-3 rounded-full bg-[#e8e1d9] mr-2"></div>
      <div className="w-3 h-3 rounded-full bg-[#e8e1d9] mr-2"></div>
      <div className="w-3 h-3 rounded-full bg-[#e8e1d9]"></div>
      <div className="mx-auto text-sm text-[#5d5a58] font-medium">Chat Preview</div>
    </div>
    <div className="p-4">
      <div className="flex mb-4">
        <div className="w-8 h-8 rounded-full bg-[#2c6694] flex items-center justify-center text-white mr-2">👤</div>
        <div className="bg-[#f1ede7] rounded-lg p-3 max-w-[80%]">
          <p className="text-[#3c3836]">What are the main components of this codebase?</p>
        </div>
      </div>
      <div className="flex mb-4 justify-end">
        <div className="bg-[#e8f4ff] rounded-lg p-3 max-w-[80%]">
          <p className="text-[#3c3836]">The main components of this codebase are:</p>
          <ul className="list-disc pl-5 text-[#5d5a58] mt-2">
            <li>UI components in the <code>src/components</code> directory</li>
            <li>API services in the <code>src/services</code> directory</li>
            <li>State management using React Context in <code>src/context</code></li>
          </ul>
        </div>
        <div className="w-8 h-8 rounded-full bg-[#3d85c6] flex items-center justify-center text-white ml-2">🤖</div>
      </div>
    </div>
  </div>
);

const Home: React.FC = () => {
  const { repositories, activeRepository } = useRepositories();
  const { messages, isLoading: chatLoading } = useChat();
  const navigate = useNavigate();

  const handleAddRepository = (e: React.MouseEvent) => {
    e.preventDefault();
    navigate('/settings');
  };

  // Display welcome screen if no repository is selected
  if (!activeRepository) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold mb-4 text-[#2c6694]">Welcome to ActuaMind</h1>
          <p className="text-xl text-[#5d5a58] max-w-2xl mx-auto">
            Your Enterprise AI Knowledge Platform for understanding and navigating complex codebases
          </p>
        </div>

        <IngestionStatus className="mb-6" />

        <ChatPreview />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
          <FeatureCard 
            title="Repository Analysis" 
            description="Add your code repositories and let ActuaMind analyze and understand them."
            icon="📊"
          />
          <FeatureCard 
            title="Natural Language Queries" 
            description="Ask questions about your code in plain English and get accurate answers."
            icon="💬"
          />
          <FeatureCard 
            title="Code Navigation" 
            description="Quickly find relevant code snippets and understand their context."
            icon="🧭"
          />
          <FeatureCard 
            title="Knowledge Extraction" 
            description="Extract insights and documentation from your codebase automatically."
            icon="🧠"
          />
        </div>

        <div className="bg-[#f1ede7] p-6 rounded-lg border border-[#e8e1d9]">
          <h2 className="text-xl font-semibold mb-4 text-[#2c6694]">Get Started</h2>
          <p className="mb-6 text-[#3c3836]">
            To begin using ActuaMind, add your first repository:
          </p>
          
          <a 
            href="/settings"
            onClick={handleAddRepository}
            className="inline-flex items-center px-6 py-3 bg-[#2c6694] text-white rounded-lg hover:bg-[#3d85c6] transition-all duration-300 transform hover:scale-105"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clipRule="evenodd" />
            </svg>
            Add Your First Repository
          </a>
          
          {repositories.length > 0 && (
            <div className="mt-8">
              <h3 className="font-medium mb-4 text-[#3c3836]">Your Repositories:</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {repositories.slice(0, 3).map(repo => (
                  <div 
                    key={repo.id}
                    className="bg-white p-4 rounded-lg shadow-sm cursor-pointer hover:shadow transition-shadow border border-[#e8e1d9]"
                  >
                    <h3 className="font-medium text-[#2c6694]">{repo.name}</h3>
                    {repo.description && (
                      <p className="text-sm text-[#5d5a58] mt-1">{repo.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Main chat interface when a repository is selected
  return (
    <div className="h-full flex flex-col">
      <IngestionStatus className="mx-4 mt-4" />
      
      <div className="flex-1 overflow-y-auto bg-[#f8f5f0]">
        {/* Chat messages will be displayed here */}
        {messages.length === 0 ? (
          <div className="text-center p-8">
            <h2 className="text-2xl font-bold mb-4 text-[#2c6694]">Ask a question about {activeRepository.name}</h2>
            <p className="text-[#5d5a58] mb-8">
              Ask any question about the codebase and ActuaMind will provide detailed answers
            </p>
            <div className="max-w-2xl mx-auto">
              <h3 className="font-medium mb-3 text-[#3c3836]">Try these example questions:</h3>
              <div className="grid grid-cols-1 gap-3">
                <ExampleQuestion text="What are the main components of this codebase?" />
                <ExampleQuestion text="How does the authentication system work?" />
                <ExampleQuestion text="Explain the data flow in the application" />
                <ExampleQuestion text="What design patterns are used in this project?" />
              </div>
            </div>
          </div>
        ) : (
          <div className="p-4">
            {/* Message list component will be added here */}
          </div>
        )}
      </div>
      
      <div className="border-t border-[#e8e1d9] p-4 bg-white">
        {/* Chat input component will be added here */}
        <div className="relative max-w-4xl mx-auto">
          <input
            type="text"
            placeholder="Ask a question about the codebase..."
            className="w-full p-3 pr-12 border border-[#e8e1d9] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2c6694] bg-[#fffaf0]"
            disabled={chatLoading}
          />
          <button
            className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-[#2c6694] text-white p-2 rounded-full hover:bg-[#3d85c6] transition-colors"
            disabled={chatLoading}
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
};

export default Home;
