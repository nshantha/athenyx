'use server'
import 'server-only'
import { createServerActionClient } from '@supabase/auth-helpers-nextjs'
import { cookies } from 'next/headers'
import { Database } from '@/lib/db_types'
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'

import { type Chat, type Result } from '@/lib/types'
import { nanoid } from '@/lib/utils'

// Function to generate a UUID v4 compatible with the database
function generateUUID() {
  // Create a proper UUID v4 string
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

export async function createChat(initialMessage?: { content: string; role: string }): Promise<{ id: string } | { error: string }> {
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    
    // Get the current user
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      return { error: 'Unauthorized' }
    }
    
    // Use UUID instead of nanoid
    const chatId = generateUUID()
    
    // Prepare initial messages array
    const initialMessages = initialMessage ? [initialMessage] : []
    
    // Create a new chat
    const chat: Chat = {
      id: chatId,
      title: initialMessage?.content ? initialMessage.content.substring(0, 30) + (initialMessage.content.length > 30 ? '...' : '') : 'New Chat',
      createdAt: new Date(),
      userId: user.id,
      path: `/chat/${chatId}`,
      messages: initialMessages
    }
    
    console.log('Creating new chat with ID:', chatId);
    
    // Insert the chat into the database with retry logic
    let attempts = 0;
    let success = false;
    let error = null;
    
    while (attempts < 3 && !success) {
      attempts++;
      console.log(`Chat creation attempt ${attempts} for ID: ${chatId}`);
      
      try {
        const result = await supabase
          .from('chats')
          .insert({
            id: chatId,
            user_id: user.id,
            payload: chat
          });
        
        if (result.error) {
          console.error(`Attempt ${attempts} failed:`, result.error);
          error = result.error;
          // Wait a bit before retrying
          await new Promise(resolve => setTimeout(resolve, 300));
        } else {
          success = true;
          error = null;
        }
      } catch (err) {
        console.error(`Attempt ${attempts} error:`, err);
        error = err;
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 300));
      }
    }
    
    if (!success) {
      console.error('All attempts to create chat failed:', error);
      return { error: 'Failed to create chat after multiple attempts' };
    }
    
    console.log('Chat created successfully in database:', chatId);
    
    // Extra verification step - check if chat was actually inserted
    const { data: verifyData, error: verifyError } = await supabase
      .from('chats')
      .select('id')
      .eq('id', chatId)
      .single();
    
    if (verifyError || !verifyData) {
      console.error('Chat creation verification failed:', verifyError);
      return { error: 'Chat creation could not be verified in database' };
    }
    
    console.log('Chat creation verified in database:', verifyData);
    
    // Make sure to revalidate both the home path and the new chat path
    revalidatePath('/')
    revalidatePath(`/chat/${chatId}`)
    
    // Dispatch custom event for realtime updates
    console.log('Chat created and stored in database, returning ID:', chatId);
    
    return { id: chatId }
  } catch (error) {
    console.error('Error in createChat:', error)
    return { error: 'Failed to create chat' }
  }
}

export async function getChats(userId?: string | null): Promise<Chat[]> {
  if (!userId) {
    console.log('No userId provided to getChats');
    return []
  }
  
  console.log('Getting all chats for userId:', userId);
  
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    
    // Get all chats for this user from the database, ordered by payload's creation date
    const { data, error } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('user_id', userId)
      .order('payload->createdAt', { ascending: false })
      .throwOnError()

    if (error) {
      console.error('Error fetching chats for user:', error);
      return [];
    }
    
    if (!data || data.length === 0) {
      console.log('No chats found for user:', userId);
      return [];
    }
    
    console.log(`Found ${data.length} chats for user:`, userId);
    
    // Extract and return the payload from each chat record
    const chats = data.map(record => {
      const payload = record.payload as Chat;
      
      // Ensure each chat has a valid ID (use database ID if payload ID is missing)
      if (!payload.id) {
        payload.id = record.id;
      }
      
      return payload;
    });
    
    return chats;
  } catch (error) {
    console.error('Exception in getChats:', error);
    return []
  }
}

export async function getChat(id: string): Promise<Chat | null> {
  console.log('getChat called with id:', id);
  
  if (!id) {
    console.error('No ID provided to getChat');
    return null;
  }
  
  const cookieStore = cookies()
  const supabase = createServerActionClient<Database>({
    cookies: () => cookieStore
  })
  
  // Get current user
  const { data: { user } } = await supabase.auth.getUser()
  console.log('Current user:', user?.id);
  
  if (!user) {
    console.error('No authenticated user found');
    return null;
  }
  
  console.log('Fetching chat with id:', id, 'directly from database');
  
  // First try by database record ID directly
  let { data, error } = await supabase
    .from('chats')
    .select('payload, id, user_id')
    .eq('id', id)
    .maybeSingle()
  
  // If not found, try searching by payload ID 
  if (!data && !error) {
    console.log('No chat found by database ID, trying with payload ID');
    const payloadResult = await supabase
      .from('chats')
      .select('payload, id, user_id')
      .filter('payload->>id', 'eq', id)
      .eq('user_id', user.id)
      .maybeSingle();
    
    if (payloadResult.data) {
      data = payloadResult.data;
      console.log('Found chat by payload ID');
    } else if (payloadResult.error) {
      error = payloadResult.error;
    }
  }
  
  console.log('Database query result:', { found: !!data, error: error });
  
  if (error) {
    console.error('Error fetching chat from database:', error);
    return null;
  }
  
  if (!data) {
    console.log('No chat found in database with id:', id);
    return null;
  }
  
  console.log('Retrieved chat from database. DB ID:', data.id, 'Payload:', data.payload);
  let chatData = data.payload as Chat;
  
  // Make sure payload has the correct ID and userId
  if (chatData) {
    // Always ensure the payload ID matches the database record ID
    if (chatData.id !== data.id) {
      console.log(`Correcting ID mismatch: payload.id=${chatData.id}, database.id=${data.id}`);
      chatData.id = data.id;
    }
    
    // Ensure userId is correct
    if (chatData.userId !== data.user_id) {
      console.log(`Correcting userId mismatch: payload.userId=${chatData.userId}, database.user_id=${data.user_id}`);
      chatData.userId = data.user_id || '';
    }
    
    // Set path correctly
    chatData.path = `/chat/${data.id}`;
    
    // Make sure messages array exists
    if (!chatData.messages) {
      console.log('Chat has no messages array, initializing empty array');
      chatData.messages = [];
    }
    
    // Update the database with the corrected payload
    const updateResult = await supabase
      .from('chats')
      .update({ payload: chatData })
      .eq('id', data.id);
      
    if (updateResult.error) {
      console.error('Failed to update chat payload with corrected data:', updateResult.error);
    } else {
      console.log('Updated chat in database with corrected payload data');
    }
  }
  
  return chatData || null;
}

export async function removeChat({ id, path }: { id: string; path: string }): Promise<Result | { error: string }> {
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    await supabase.from('chats').delete().eq('id', id).throwOnError()

    revalidatePath('/')
    revalidatePath(path)
    return { data: undefined } as Result
  } catch (error) {
    return {
      error: 'Unauthorized'
    }
  }
}

export async function clearChats(): Promise<Result | { error: string }> {
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    await supabase.from('chats').delete().throwOnError()
    revalidatePath('/')
    redirect('/')
    return { data: undefined } as Result
  } catch (error) {
    console.log('clear chats error', error)
    return {
      error: 'Unauthorized'
    }
  }
}

export async function getSharedChat(id: string): Promise<Chat | null> {
  const cookieStore = cookies()
  const supabase = createServerActionClient<Database>({
    cookies: () => cookieStore
  })
  const { data } = await supabase
    .from('chats')
    .select('payload')
    .eq('id', id)
    .not('payload->sharePath', 'is', null)
    .maybeSingle()

  return (data?.payload as Chat) ?? null
}

export async function shareChat(chat: Chat): Promise<Chat | { error: string }> {
  try {
    const payload = {
      ...chat,
      sharePath: `/share/${chat.id}`
    }

    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    await supabase
      .from('chats')
      .update({ payload: payload as any })
      .eq('id', chat.id)
      .throwOnError()

    return payload
  } catch (error) {
    return {
      error: 'Failed to share chat'
    }
  }
}

export async function updateChat(
  chatId: string,
  messages: any[]
): Promise<{ id: string } | { error: string }> {
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    
    // Get the current chat
    const { data } = await supabase
      .from('chats')
      .select('payload')
      .eq('id', chatId)
      .maybeSingle()
    
    if (!data) {
      return { error: 'Chat not found' }
    }
    
    const chat = data.payload as Chat
    console.log('Current chat title:', chat.title)
    console.log('Messages length:', messages.length)
    
    // Update the chat with new messages
    const updatedChat = {
      ...chat,
      messages,
      // Convert Date to string for JSON serialization
      createdAt: chat.createdAt instanceof Date ? chat.createdAt.toISOString() : chat.createdAt
    }
    
    // Only update the title if it's "New Chat" or if there was no title before
    let titleChanged = false;
    if ((chat.title === 'New Chat' || !chat.title) && messages.length > 0) {
      const firstUserMessage = messages.find(m => m.role === 'user')
      if (firstUserMessage) {
        // Use the first ~30 chars of the first user message as the title
        const newTitle = firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '');
        
        // Only update if the title is actually different
        if (newTitle !== chat.title) {
          updatedChat.title = newTitle;
          titleChanged = true;
          console.log('Updated title to:', updatedChat.title);
        }
      }
    }
    
    // Only update in the database if messages changed or title changed
    const messagesChanged = JSON.stringify(chat.messages) !== JSON.stringify(messages);
    if (messagesChanged || titleChanged) {
      // Save the updated chat
      const { error } = await supabase
        .from('chats')
        .update({ payload: updatedChat })
        .eq('id', chatId)
      
      if (error) {
        console.error('Error updating chat in database:', error)
        return { error: 'Failed to update chat' }
      }
      
      console.log('Chat updated successfully with title:', updatedChat.title)
      
      // Only revalidate paths if something actually changed
      revalidatePath(`/chat/${chatId}`)
      if (titleChanged) {
        revalidatePath('/') // Only revalidate home if title changed
      }
    } else {
      console.log('No changes detected, skipping database update')
    }
    
    return { id: chatId }
  } catch (error) {
    console.error('Error updating chat:', error)
    return { error: 'Failed to update chat' }
  }
}

/**
 * Search chats by content or title
 * @param query The search query
 * @returns Array of chats that match the search criteria
 */
export async function searchChats(query: string): Promise<Chat[]> {
  if (!query?.trim()) {
    return []
  }
  
  try {
    const cookieStore = cookies()
    const supabase = createServerActionClient<Database>({
      cookies: () => cookieStore
    })
    
    // Get current user
    const { data: { user } } = await supabase.auth.getUser()
    
    if (!user) {
      console.error('No authenticated user found for search')
      return []
    }
    
    console.log(`Searching chats for user ${user.id} with query: ${query}`)
    
    // First search by title using ilike for partial matches
    const { data: titleResults, error: titleError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('user_id', user.id)
      .ilike('payload->>title', `%${query}%`)
      .order('payload->createdAt', { ascending: false })
    
    if (titleError) {
      console.error('Error searching chats by title:', titleError)
    }
    
    // Then search message content using a more generic approach
    // Not as effective but works without custom functions
    const { data: messageResults, error: messageError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('user_id', user.id)
      .filter('payload', 'cs', `{"messages":[{"content":"${query}"`)
      .order('payload->createdAt', { ascending: false })
    
    if (messageError) {
      console.error('Error searching chats by message content:', messageError)
    }
    
    // Combine results, removing duplicates
    const allResults = [...(titleResults || []), ...(messageResults || [])]
    const uniqueResults = allResults.filter((chat, index, self) => 
      index === self.findIndex(c => c.id === chat.id)
    )
    
    console.log(`Search found ${uniqueResults.length} results`)
    
    // Format the results to return Chat objects
    return uniqueResults.map(record => {
      const payload = record.payload as Chat
      
      // Ensure each chat has a valid ID
      if (!payload.id) {
        payload.id = record.id
      }
      
      return payload
    })
  } catch (error) {
    console.error('Exception in searchChats:', error)
    return []
  }
}
