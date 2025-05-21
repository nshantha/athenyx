import { auth } from '@/auth'
import { createServerComponentClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { NextRequest, NextResponse } from 'next/server'
import { Database } from '@/lib/db_types'

export async function POST(req: NextRequest) {
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
  
  if (!session?.user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    )
  }
  
  try {
    const { chatId, messages, title } = await req.json()
    
    // Create Supabase client
    const supabase = createServerComponentClient<Database>({
      cookies: () => cookieStore
    })
    
    // Get the chat if it exists
    const { data: existingChat } = await supabase
      .from('chats')
      .select('payload')
      .eq('id', chatId)
      .maybeSingle()
    
    // Prepare the chat payload with updated data
    const chat = existingChat?.payload || {
      id: chatId,
      title: title || 'New Chat',
      createdAt: new Date().toISOString(),
      userId: session.user.id,
      path: `/chat/${chatId}`
    }
    
    // Update messages if provided
    if (messages) {
      chat.messages = messages
    }
    
    // Update title if this is the first user message and title is still default
    if (messages?.length > 0 && (chat.title === 'New Chat' || !chat.title)) {
      const firstUserMessage = messages.find(m => m.role === 'user')
      if (firstUserMessage) {
        chat.title = firstUserMessage.content.substring(0, 30) + 
          (firstUserMessage.content.length > 30 ? '...' : '')
      }
    }
    
    // Insert or update in database based on whether it exists
    let result
    if (existingChat) {
      // Update existing chat
      result = await supabase
        .from('chats')
        .update({
          payload: chat
        })
        .eq('id', chatId)
    } else {
      // Insert new chat
      result = await supabase
        .from('chats')
        .insert({
          id: chatId,
          user_id: session.user.id,
          payload: chat
        })
    }
    
    if (result.error) {
      throw result.error
    }
    
    return NextResponse.json({ success: true, chatId })
  } catch (error) {
    console.error('Error in chat API route:', error)
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    )
  }
}