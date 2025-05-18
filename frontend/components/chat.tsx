'use client'

import React, { useState, useEffect, useRef } from 'react'
import { cn } from '@/lib/utils'
import { ChatList } from '@/components/chat-list'
import { ChatPanel } from '@/components/chat-panel'
import { EmptyScreen } from '@/components/empty-screen'
import { ChatScrollAnchor } from '@/components/chat-scroll-anchor'
import { toast } from 'react-hot-toast'
import { useRepository } from '@/lib/repository-context'
import { queryApi } from '@/lib/api'
import { nanoid } from '@/lib/utils'
import { Message } from '@/lib/types'

export interface ChatProps {
  initialMessages?: Message[]
  id?: string
  className?: string
}

export function Chat({ id = nanoid(), initialMessages = [], className }: ChatProps) {
  // State for messages
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // Get active repository from context
  const { activeRepository } = useRepository()
  
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
    
    try {
      // Prepare conversation history
      let conversationHistory = ''
      if (messages.length > 0) {
        conversationHistory = messages.map(msg => {
          const prefix = msg.role === 'user' ? 'User: ' : 'Assistant: '
          return prefix + msg.content
        }).join('\n\n')
      }
      
      // Prepare query request
      const queryRequest = {
        query: content,
        conversation_history: conversationHistory || null,
        repository_url: activeRepository?.url
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
              // We need to be careful with newlines as they're important for markdown
              const processedData = data
                // For newlines, escape sequences, and other characters that might appear in the SSE stream
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
        }
      } catch (apiError: any) {
        console.error('API error:', apiError)
        
        // Create an error message
        const errorMessage: Message = {
          id: nanoid(),
          content: `Sorry, I encountered an error: ${apiError.message || 'Failed to connect to the API. Please check if the backend server is running.'}`,
          role: 'assistant'
        }
        
        setMessages(prev => [...prev, errorMessage])
      }
      
      setIsLoading(false)
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
  
  return (
    <>
      <div className={cn('pb-[200px] pt-4 md:pt-10 max-w-3xl mx-auto', className)}>
        {messages.length ? (
          <>
            <ChatList messages={messages} />
            <ChatScrollAnchor trackVisibility={isLoading} />
          </>
        ) : (
          <EmptyScreen setInput={setInput} />
        )}
      </div>
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
  )
}
