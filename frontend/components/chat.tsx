'use client'

import React, { useState, useEffect, useRef } from 'react'
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
import { updateChat } from '@/app/actions'

export interface ChatProps {
  initialMessages?: Message[]
  id?: string
  className?: string
}

export function Chat({ id = nanoid(), initialMessages = [], className }: ChatProps) {
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
  
  // Save messages to database when they change
  useEffect(() => {
    // Don't save if there are no messages or if we're still loading
    if (messages.length === 0 || isLoading) return
    
    // Don't save if these are just the initial messages
    if (JSON.stringify(messages) === JSON.stringify(initialMessages)) return
    
    // Use a debounce mechanism to avoid too frequent updates
    const timeoutId = setTimeout(() => {
      // Save messages to database
      const saveMessages = async () => {
        try {
          console.log('Saving chat with id:', id, 'and messages:', messages.length);
          const result = await updateChat(id, messages)
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
        
        // Create a temporary message for streaming
        const assistantMessage: Message = {
          id: nanoid(),
          content: '',
          role: 'assistant'
        }
        
        setMessages(prev => [...prev, assistantMessage])
        
        // Scroll to bottom again after adding assistant message
        setTimeout(scrollToBottom, 100)
        
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