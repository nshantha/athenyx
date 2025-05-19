// Script to create a test chat in the database
import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'

// Use built-in UUID generator
function uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

// Load environment variables
dotenv.config()

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY

// Check required environment variables
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('Missing required environment variables')
  process.exit(1)
}

// Create Supabase client
// NOTE: This will only work if authenticated in the browser or if RLS is disabled
console.log('Using Supabase client with anon key - will only work if authenticated or if RLS is disabled')
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

async function createTestChat() {
  try {
    console.log('===== Create Test Chat =====')
    
    // Ask for userId (optional - defaults to first user found)
    const userId = process.argv[2] || await getFirstUserId()
    
    if (!userId) {
      console.error('No userId provided and no users found in database.')
      process.exit(1)
    }
    
    // Generate a new UUID for the chat
    const chatId = uuidv4()
    
    // Create a test chat object
    const chat = {
      id: chatId,
      title: 'Test Chat ' + new Date().toLocaleTimeString(),
      createdAt: new Date(),
      userId: userId,
      path: `/chat/${chatId}`,
      messages: [
        {
          id: uuidv4(),
          content: 'Hello, this is a test message',
          role: 'user',
          createdAt: new Date()
        },
        {
          id: uuidv4(),
          content: 'Hello! I am an AI assistant. How can I help you today?',
          role: 'assistant',
          createdAt: new Date()
        }
      ]
    }
    
    console.log('Creating chat with ID:', chatId)
    console.log('Chat will be associated with userId:', userId)
    
    // Insert into database
    const { data, error } = await supabase
      .from('chats')
      .insert({
        id: chatId,
        user_id: userId,
        payload: chat
      })
    
    if (error) {
      console.error('Error creating chat:', error)
      process.exit(1)
    }
    
    console.log('✅ Chat created successfully')
    console.log('Chat ID:', chatId)
    console.log('URL: http://localhost:3000/chat/' + chatId)
    
    // Verify the chat was created
    const { data: verifyData, error: verifyError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('id', chatId)
      .single()
    
    if (verifyError) {
      console.error('Error verifying chat creation:', verifyError)
    } else {
      console.log('Chat verified in database:', verifyData.id)
      console.log('Payload ID:', verifyData.payload?.id)
      console.log('Title:', verifyData.payload?.title)
    }
    
    // List all chats for this user to verify it would appear in UI
    console.log('\nListing all chats for this user:')
    const { data: userChats, error: userChatsError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('user_id', userId)
    
    if (userChatsError) {
      console.error('Error listing user chats:', userChatsError)
    } else {
      console.log(`Found ${userChats?.length || 0} chats for user`)
      if (userChats && userChats.length > 0) {
        for (const chat of userChats) {
          console.log(`- Chat ID: ${chat.id}, Title: ${chat.payload?.title}`)
        }
      }
    }
  } catch (error) {
    console.error('Unhandled error:', error)
    process.exit(1)
  }
}

// Helper function to get the first user ID if none is provided
async function getFirstUserId(): Promise<string | null> {
  try {
    console.log('No userId provided, attempting to find the first user...')
    
    // Try to get any chat to extract a valid user_id
    const { data: chatData } = await supabase
      .from('chats')
      .select('user_id')
      .limit(1)
      .single()
    
    if (chatData?.user_id) {
      console.log('Found userId from existing chat:', chatData.user_id)
      return chatData.user_id
    }
    
    // If no chats exist, we can't find users
    // Note: Regular clients can't list users, would need admin access
    console.log('No chats found, cannot determine user ID')
    return null
  } catch (error) {
    console.error('Error finding first user:', error)
    return null
  }
}

createTestChat() 