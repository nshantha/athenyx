import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import { 
  ChatRequest, 
  ChatResponse,
  ConversationsResponse,
  ConversationResponse,
  Message,
  MessageRole
} from '../types/chat';

const API_URL = process.env.REACT_APP_BACKEND_API_URL || 'http://localhost:8000/api';

// Send a chat message
export const sendMessage = async (request: ChatRequest): Promise<ChatResponse> => {
  // Map the ChatRequest to the backend's QueryRequest format
  const queryRequest = {
    query: request.message,
    conversation_history: null, // We're not tracking conversation history yet
    repository_url: request.repository_id, // Using repository_id as URL
    user_id: null
  };

  try {
    console.log('Sending query to API:', queryRequest);
    
    // Use fetch for streaming support instead of axios
    const response = await fetch(`${API_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(queryRequest),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    // Read the response as a stream of server-sent events
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body reader could not be created');
    }

    // Collect the entire response
    let fullText = '';
    
    // Process the stream
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // Convert the chunk to text
      const chunk = new TextDecoder().decode(value);
      
      // Parse SSE format (data: message\n\n)
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data:')) {
          const content = line.slice(5).trim();
          fullText += content + ' ';
          console.log('Received chunk:', content);
        }
      }
    }
    
    console.log('Full response text:', fullText);
    
    // Create a response message with the full text
    const assistantMessage: Message = {
      id: uuidv4(),
      role: MessageRole.ASSISTANT,
      content: fullText || "Sorry, I couldn't process your request.",
      timestamp: new Date().toISOString()
    };
    
    // Return in the expected format
    return {
      message: assistantMessage,
      conversation_id: uuidv4() // Generate a temporary conversation ID
    };
  } catch (error) {
    console.error("Error sending message:", error);
    
    // Create an error message
    const errorMessage: Message = {
      id: uuidv4(),
      role: MessageRole.ASSISTANT,
      content: "Sorry, there was an error processing your request. Please try again.",
      timestamp: new Date().toISOString()
    };
    
    // Return error response
    return {
      message: errorMessage,
      conversation_id: uuidv4()
    };
  }
};

// Get all conversations for a repository - returns mock data since endpoint doesn't exist
export const getConversations = async (repositoryId: string): Promise<ConversationsResponse> => {
  console.log('Warning: getConversations endpoint not implemented in backend, returning mock data');
  try {
    const response = await axios.get(`${API_URL}/repositories/${repositoryId}/conversations`);
    return response.data;
  } catch (error) {
    console.warn('Conversations endpoint not available, returning empty array');
    return { conversations: [] };
  }
};

// Get a specific conversation by ID - returns mock data since endpoint doesn't exist
export const getConversation = async (conversationId: string): Promise<ConversationResponse> => {
  console.log('Warning: getConversation endpoint not implemented in backend, returning mock data');
  try {
    const response = await axios.get(`${API_URL}/conversations/${conversationId}`);
    return response.data;
  } catch (error) {
    console.warn('Conversation endpoint not available, returning empty conversation');
    return { 
      conversation: {
        id: conversationId,
        title: 'Conversation',
        repository_id: '',
        messages: [],
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      } 
    };
  }
};

// Get example questions for a repository - returns hardcoded examples since endpoint doesn't exist
export const getExampleQuestions = async (repositoryId: string): Promise<string[]> => {
  console.log('Warning: getExampleQuestions endpoint not implemented in backend, returning hardcoded examples');
  try {
    const response = await axios.get(`${API_URL}/repositories/${repositoryId}/examples`);
    return response.data.examples;
  } catch (error) {
    console.warn('Examples endpoint not available, returning hardcoded examples');
    return [
      "What are the main components of this codebase?",
      "How does the authentication system work?",
      "Explain the data flow in the application",
      "What design patterns are used in this project?",
      "Show me the implementation of the main service class"
    ];
  }
};
