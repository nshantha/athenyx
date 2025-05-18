import 'server-only'
import { cookies } from 'next/headers'
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs'
import { Database } from '@/lib/db_types'
import { nanoid } from '@/lib/utils'
import { queryApi, QueryRequest } from '@/lib/api'

export const runtime = 'edge'

export async function POST(req: Request) {
  const json = await req.json()
  const { messages, previewToken, repository_url } = json
  
  if (!messages || !messages.length) {
    return new Response('No messages provided', { status: 400 })
  }
  
  try {
    // Extract the latest user message
    const latestUserMessage = messages.filter((m: any) => m.role === 'user').pop()
    
    if (!latestUserMessage) {
      return new Response('No user message found', { status: 400 })
    }
    
    // Prepare conversation history
    let conversationHistory = ''
    if (messages.length > 1) {
      // Skip the latest message as it's the current query
      const historyMessages = messages.slice(0, -1)
      conversationHistory = historyMessages.map((msg: any) => {
        const prefix = msg.role === 'user' ? 'User: ' : 'Assistant: '
        return prefix + msg.content
      }).join('\n\n')
    }
    
    // Prepare the query request
    const queryRequest: QueryRequest = {
      query: latestUserMessage.content,
      conversation_history: conversationHistory || null,
      repository_url: repository_url // Pass the repository URL if available
    }
    
    // Get the stream from the backend API
    const stream = await queryApi.streamQuery(queryRequest)
    
    // Create a TransformStream to process the response
    const { readable, writable } = new TransformStream()
    const writer = writable.getWriter()
    
    // Process the stream and save to Supabase when complete
    const reader = stream.getReader()
    let fullResponse = ''
    
    // Process stream using an arrow function to avoid strict mode issues
    const processStream = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          // Convert the chunk to text
          const chunk = new TextDecoder().decode(value)
          fullResponse += chunk
          
          // Write the chunk to the output stream
          await writer.write(value)
        }
        
        // Close the writer when done
        await writer.close()
        
        // Try to save to Supabase if we have a session
        try {
          const cookieStore = cookies()
          const supabase = createRouteHandlerClient<Database>({
            cookies: () => cookieStore
          })
          
          const { data: { session } } = await supabase.auth.getSession()
          
          if (session?.user) {
            const title = messages[0].content.substring(0, 100)
            const id = json.id ?? nanoid()
            const createdAt = Date.now()
            const path = `/chat/${id}`
            
            const payload = {
              id,
              title,
              userId: session.user.id,
              createdAt,
              path,
              messages: [
                ...messages,
                {
                  content: fullResponse,
                  role: 'assistant'
                }
              ],
              repository_url // Store the repository URL with the chat
            }
            
            // Insert chat into database
            await supabase.from('chats').upsert({ id, payload })
          }
        } catch (error) {
          console.error('Error saving chat to Supabase:', error)
          // Continue even if Supabase save fails
        }
      } catch (error) {
        console.error('Error processing stream:', error)
        await writer.abort(error as any)
      }
    }
    
    // Start processing the stream
    processStream()
    
    // Return the readable stream
    return new Response(readable)
  } catch (error: any) {
    console.error('Error in chat API route:', error)
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    })
  }
}
