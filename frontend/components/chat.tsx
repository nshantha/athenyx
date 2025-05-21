'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { ChatList } from '@/components/chat-list'
import { ChatPanel } from '@/components/chat-panel'
import { EmptyScreen } from '@/components/empty-screen'
import { ChatScrollAnchor } from '@/components/chat-scroll-anchor'
import { toast } from 'react-hot-toast'
import { useRepository } from '@/lib/repository-context'
import { useSidebar } from '@/lib/sidebar-context'
import { queryApi } from '@/lib/api'
import { nanoid } from '@/lib/utils'
import { Message } from '@/lib/types'
import { PromptForm } from '@/components/prompt-form'
import { updateChat, createChat } from '@/app/actions'

export interface ChatProps {
  initialMessages?: Message[]
  id?: string
  className?: string
}

export function Chat({ id = nanoid(), initialMessages = [], className }: ChatProps) {
  // Initialize router
  const router = useRouter()
  
  // State for messages
  const [messages, setMessages] = useState<Message[]>(initialMessages || [])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // Create a ref for the chat container
  const chatContainerRef = useRef<HTMLDivElement>(null)
  
  // Function to scroll to the bottom of the chat
  const scrollToBottom = () => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }
  
  // Debug log for initialMessages
  useEffect(() => {
    console.log('Chat component initialized with:', { 
      id, 
      initialMessagesProvided: !!initialMessages,
      messageCount: initialMessages?.length || 0
    });
  }, [id, initialMessages]);
  
  // Add an effect to scroll to bottom when messages change
  useEffect(() => {
    // Only scroll if there are messages
    if (messages.length > 0) {
      scrollToBottom();
    }
  }, [messages]);
  
  // Get active repository from context
  const { activeRepository } = useRepository()
  
  // Get sidebar state
  const { isExpanded } = useSidebar()
  
  // Separate function to process API requests without adding user message again
  const processApiRequest = async (content: string) => {
    if (!content.trim()) return;
    
    // If already loading, don't process again
    if (isLoading) {
      console.log('Already loading a response, skipping duplicate API call');
      return;
    }
    
    // Set loading state to prevent duplicate API calls
    setIsLoading(true);
    
    try {
      // Check if we already have an assistant message following this user message
      // This prevents duplicate responses to the same message
      const msgCount = messages.length;
      const hasExistingResponse = msgCount >= 2 && 
        messages[msgCount - 2].role === 'user' && 
        messages[msgCount - 1].role === 'assistant' &&
        messages[msgCount - 2].content === content;
      
      if (hasExistingResponse) {
        console.log('This message already has a response, skipping API call');
        setIsLoading(false);
        return;
      }
      // Prepare conversation history (exclude the last user message since we're processing it)
      let conversationHistory = '';
      if (messages.length > 1) { // More than just the current user message
        conversationHistory = messages.slice(0, -1).map(msg => {
          const prefix = msg.role === 'user' ? 'User: ' : 'Assistant: ';
          return prefix + msg.content;
        }).join('\n\n');
      }
      
      // Check if active repository is available
      if (!activeRepository?.url) {
        throw new Error('No active repository selected. Please select a repository in the sidebar.');
      }
      
      // Prepare query request
      const queryRequest = {
        query: content,
        conversation_history: conversationHistory || null,
        repository_url: activeRepository.url
      };
      
      // Stream the response
      try {
        const stream = await queryApi.streamQuery(queryRequest);
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        let responseText = '';
        
        // Check if we already have an empty assistant message at the end
        // If not, add a new one for streaming
        let assistantMessageExists = false;
        setMessages(prev => {
          // Check if the last message is already an empty assistant message
          if (prev.length > 0 && prev[prev.length - 1].role === 'assistant' && prev[prev.length - 1].content === '') {
            assistantMessageExists = true;
            return prev; // No change needed
          }
          
          // Otherwise, add a new assistant message
          const assistantMessage: Message = {
            id: nanoid(),
            content: '',
            role: 'assistant'
          };
          return [...prev, assistantMessage];
        });
        
        // Only scroll to bottom if we added a new message
        if (!assistantMessageExists) {
          setTimeout(scrollToBottom, 100);
        }
        
        // Read the stream
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // Decode the chunk and update the response
          const chunk = decoder.decode(value);
          
          // Process SSE format (data: prefix)
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // Extract the actual data without the prefix
              const data = line.substring(6);
              
              // Handle escaped characters that might affect markdown
              const processedData = data
                .replace(/\\n/g, '\n')
                .replace(/\\r/g, '\r')
                .replace(/\\t/g, '\t')
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, '\\');
              
              responseText += processedData;
            }
          }
          
          // Update the message with the current response
          setMessages(prev => {
            const newMessages = [...prev];
            const lastMessage = newMessages[newMessages.length - 1];
            if (lastMessage.role === 'assistant') {
              lastMessage.content = responseText;
            }
            return newMessages;
          });
          
          // Scroll to bottom periodically while receiving response
          scrollToBottom();
        }
      } catch (apiError: any) {
        // Handle API errors - same as before
        console.error('API error:', apiError);
        
        let errorMsg = 'Failed to connect to the API. Please check if the backend server is running.';
        
        if (apiError.message) {
          if (apiError.message.includes('Failed to fetch')) {
            errorMsg = 'Unable to connect to the server. Please check your internet connection or try again later.';
          } else {
            errorMsg = `Error: ${apiError.message}`;
          }
        }
        
        const errorMessage: Message = {
          id: nanoid(),
          content: errorMsg,
          role: 'assistant'
        };
        
        setMessages(prev => {
          // Remove empty assistant message if exists
          const filtered = prev.filter(m => !(m.role === 'assistant' && !m.content));
          return [...filtered, errorMessage];
        });
      }
      
    } catch (error) {
      // Handle general errors - same as before
      console.error('Error processing API request:', error);
      toast.error('Failed to process request');
      
      const errorMessage: Message = {
        id: nanoid(),
        content: 'Sorry, an error occurred while processing your message. Please try again later.',
        role: 'assistant'
      };
      
      setMessages(prev => {
        // Remove any empty assistant messages
        const filtered = prev.filter(m => !(m.role === 'assistant' && !m.content));
        return [...filtered, errorMessage];
      });
    } finally {
      setIsLoading(false);
      // Final scroll to bottom
      setTimeout(scrollToBottom, 100);
    }
  };
  
  // When chat is loaded, check if there are unanswered questions
  useEffect(() => {
    // Only run this effect on initial load or when messages change from external source
    // Skip if loading is in progress
    if (isLoading) return;
    
    // Track if the effect has run to prevent duplicate calls
    const hasUserMessageWithoutResponse = messages.length > 0 && 
      messages[messages.length - 1].role === 'user';
    
    // Only proceed if we have a valid chat ID (not 'new' or empty)
    if (hasUserMessageWithoutResponse && id && id !== 'new') {
      console.log('Found unanswered question, auto-triggering API call');
      
      // Get the last user message
      const lastUserMessage = messages[messages.length - 1];
      
      // Use a small timeout to prevent race conditions with state updates
      const timeoutId = setTimeout(() => {
        // Double check we're not already loading
        if (!isLoading) {
          // Send the message to the API without adding it to messages again
          processApiRequest(lastUserMessage.content);
        }
      }, 100);
      
      // Clean up timeout if component unmounts or effect re-runs
      return () => clearTimeout(timeoutId);
    }
  }, [id, isLoading]); // Only depend on id and loading state, not messages or initialMessages
  
  // Save messages to database when they change
  useEffect(() => {
    // Don't save if there are no messages or if we're still loading
    if (messages.length === 0 || isLoading) return
    
    // Don't save if these are just the initial messages
    if (JSON.stringify(messages) === JSON.stringify(initialMessages)) return
    
    // Don't save if we don't have a valid ID yet
    if (!id || id === 'new') return
    
    // Use a debounce mechanism to avoid too frequent updates
    const timeoutId = setTimeout(() => {
      // Save messages to database using API endpoint
      const saveMessages = async () => {
        try {
          console.log('Saving chat with id:', id, 'and messages:', messages.length);
          
          // Use the new API endpoint instead of server action
          const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              chatId: id,
              messages: messages
            })
          });
          
          if (!response.ok) {
            throw new Error(`Failed to save messages: ${response.statusText}`);
          }
          
          const result = await response.json();
          console.log('Save result:', result);
        } catch (error) {
          console.error('Failed to save messages:', error)
        }
      }
      
      saveMessages()
    }, 1000) // Wait 1 second before saving to avoid rapid consecutive updates
    
    // Clear timeout if effect runs again before timeout completes
    return () => clearTimeout(timeoutId)
  }, [messages, id, isLoading, initialMessages])
  
  // Function to send a message
  const sendMessage = async (content: string) => {
    if (!content.trim()) return
    
    // Add user message to state
    const userMessage: Message = {
      id: nanoid(),
      content,
      role: 'user'
    }
    
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    
    // Scroll to bottom when starting to send a message
    setTimeout(scrollToBottom, 100)
    
    try {
      // If this is a brand new chat with no ID or default ID, create it now with the message
      if (!id || id === 'new') {
        console.log('Creating new chat on first message with content:', content);
        
        // Create a chat with the initial message already included
        const result = await createChat({ 
          content: content,
          role: 'user' 
        });
        
        if ('error' in result) {
          throw new Error(`Failed to create chat: ${result.error}`);
        }
        
        // Get the new chat ID
        const newId = result.id;
        console.log('Created new chat with ID:', newId);
        
        // Navigate to the new chat page
        router.push(`/chat/${newId}`);
        return; // Early return to let the navigation complete
      }
      
      // Prepare conversation history
      let conversationHistory = ''
      if (messages.length > 0) {
        conversationHistory = messages.map(msg => {
          const prefix = msg.role === 'user' ? 'User: ' : 'Assistant: '
          return prefix + msg.content
        }).join('\n\n')
      }
      
      // Check if active repository is available
      if (!activeRepository?.url) {
        throw new Error('No active repository selected. Please select a repository in the sidebar.')
      }
      
      // Prepare query request
      const queryRequest = {
        query: content,
        conversation_history: conversationHistory || null,
        repository_url: activeRepository.url
      }
      
      // Stream the response
      try {
        const stream = await queryApi.streamQuery(queryRequest)
        const reader = stream.getReader()
        const decoder = new TextDecoder()
        let responseText = ''
        
        // Check if we already have an empty assistant message at the end
        // If not, add a new one for streaming
        let assistantMessageExists = false;
        setMessages(prev => {
          // Check if the last message is already an empty assistant message
          if (prev.length > 0 && prev[prev.length - 1].role === 'assistant' && prev[prev.length - 1].content === '') {
            assistantMessageExists = true;
            return prev; // No change needed
          }
          
          // Otherwise, add a new assistant message
          const assistantMessage: Message = {
            id: nanoid(),
            content: '',
            role: 'assistant'
          };
          return [...prev, assistantMessage];
        });
        
        // Only scroll to bottom if we added a new message
        if (!assistantMessageExists) {
          setTimeout(scrollToBottom, 100);
        }
        
        // Read the stream
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          // Decode the chunk and update the response
          const chunk = decoder.decode(value)
          
          // Process SSE format (data: prefix)
          const lines = chunk.split('\n')
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // Extract the actual data without the prefix
              const data = line.substring(6)
              
              // Handle escaped characters that might affect markdown
              const processedData = data
                .replace(/\\n/g, '\n')
                .replace(/\\r/g, '\r')
                .replace(/\\t/g, '\t')
                .replace(/\\"/g, '"')
                .replace(/\\\\/g, '\\')
              
              responseText += processedData
            }
          }
          
          // Update the message with the current response
          setMessages(prev => {
            const newMessages = [...prev]
            const lastMessage = newMessages[newMessages.length - 1]
            if (lastMessage.role === 'assistant') {
              lastMessage.content = responseText
            }
            return newMessages
          })
          
          // Scroll to bottom periodically while receiving response
          scrollToBottom()
        }
      } catch (apiError: any) {
        console.error('API error:', apiError)
        
        // Create a more user-friendly error message
        let errorMsg = 'Failed to connect to the API. Please check if the backend server is running.'
        
        if (apiError.message) {
          if (apiError.message.includes('Failed to fetch')) {
            errorMsg = 'Unable to connect to the server. Please check your internet connection or try again later.'
          } else {
            errorMsg = `Error: ${apiError.message}`
          }
        }
        
        const errorMessage: Message = {
          id: nanoid(),
          content: errorMsg,
          role: 'assistant'
        }
        
        setMessages(prev => {
          // Remove empty assistant message if exists
          const filtered = prev.filter(m => !(m.role === 'assistant' && !m.content))
          return [...filtered, errorMessage]
        })
      }
      
      setIsLoading(false)
      // Final scroll to bottom after completion
      setTimeout(scrollToBottom, 100)
      
    } catch (error) {
      console.error('Error sending message:', error)
      toast.error('Failed to send message')
      setIsLoading(false)
      
      // Remove the last assistant message if it exists
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1]
        if (lastMessage.role === 'assistant' && !lastMessage.content) {
          return prev.slice(0, -1)
        }
        return prev
      })
      
      // Add an error message
      const errorMessage: Message = {
        id: nanoid(),
        content: 'Sorry, an error occurred while processing your message. Please try again later.',
        role: 'assistant'
      }
      
      setMessages(prev => [...prev, errorMessage])
      
      // Scroll to bottom after error message
      setTimeout(scrollToBottom, 100)
    }
  }
  
  // Function to handle form submission
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    sendMessage(input)
    setInput('')
  }
  
  // Function to stop generation (not implemented yet)
  const stop = () => {
    // This would require aborting the fetch request
    // For now, just set isLoading to false
    setIsLoading(false)
  }
  
  // Function to reload the last message
  const reload = () => {
    // Find the last user message
    const lastUserMessageIndex = [...messages].reverse().findIndex(m => m.role === 'user')
    if (lastUserMessageIndex >= 0) {
      const lastUserMessage = messages[messages.length - 1 - lastUserMessageIndex]
      // Remove the last assistant message if it exists
      setMessages(prev => {
        const lastMessage = prev[prev.length - 1]
        if (lastMessage.role === 'assistant') {
          return prev.slice(0, -1)
        }
        return prev
      })
      // Resend the last user message
      sendMessage(lastUserMessage.content)
    }
  }
  
  // Check if we should display the empty screen with centered prompt
  const isEmpty = messages.length === 0
  
  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {isEmpty ? (
        // Empty screen with centered prompt
        <div className="flex-1 flex flex-col items-center justify-center transition-all duration-300 ease-in-out">
          <div className="w-full max-w-3xl px-4">
            <EmptyScreen setInput={setInput} />
            <div className="mt-8">
              <PromptForm
                onSubmit={async (value) => {
                  await sendMessage(value);
                }}
                input={input}
                setInput={setInput}
                isLoading={isLoading}
                isEmptyScreen={true}
              />
            </div>
          </div>
        </div>
      ) : (
        // Chat interface with messages and bottom prompt
        <>
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto pb-[120px] pt-4 md:pt-10 transition-all duration-300 ease-in-out"
          >
            <div className="w-full max-w-3xl mx-auto px-4 md:px-8 lg:px-10">
              <ChatList messages={messages} />
              <ChatScrollAnchor trackVisibility={isLoading} />
            </div>
          </div>
          
          {/* Fixed position ChatPanel with centered content */}
          <ChatPanel
            id={id}
            isLoading={isLoading}
            stop={stop}
            append={(message: { content: string }) => sendMessage(message.content)}
            reload={reload}
            messages={messages}
            input={input}
            setInput={setInput}
            onSubmit={handleSubmit}
          />
        </>
      )}
    </div>
  )
}