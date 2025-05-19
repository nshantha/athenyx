// This script helps sync chats from browser's localStorage to the database
import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import fs from 'fs'
import readline from 'readline'

// Load environment variables
dotenv.config()

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

// Check required environment variables
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.error('Missing required environment variables')
  process.exit(1)
}

// Create Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// Create readline interface
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
})

// Helper function to prompt for input
const prompt = (question: string): Promise<string> => {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer)
    })
  })
}

// Chat IDs we want to fix
const chatIds = [
  '2f8ff17c-19e6-4c7a-a369-27f23d48bbd3',
  '7ac0def5-d9ef-42f9-9b9d-076b36e8d1f5',
  'abb15092-27fe-40d6-9d18-497fa527c7de',
  'ecb548c3-317b-4507-bddb-3f154e921b53'
]

async function main() {
  console.log('===== Chat Database Sync Tool =====')
  console.log('This tool will help sync chats to the database')
  console.log('----------------------------------')
  
  // Check if we can access the database
  const { data: tablesData, error: tablesError } = await supabase
    .from('chats')
    .select('count')
    .limit(1)
  
  if (tablesError) {
    console.error('Error accessing database:', tablesError)
    process.exit(1)
  }
  
  console.log('✅ Database connection successful')
  
  // Get user authentication
  console.log('\nFirst, we need to authenticate you...')
  const email = await prompt('Enter your email: ')
  const password = await prompt('Enter your password: ')
  
  console.log('\nAttempting to sign in...')
  const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
    email,
    password
  })
  
  if (authError) {
    console.error('Authentication failed:', authError)
    rl.close()
    process.exit(1)
  }
  
  const userId = authData?.user?.id
  console.log(`✅ Authentication successful. User ID: ${userId}`)
  
  console.log('\nNow we need chat data to restore...')
  console.log('Options:')
  console.log('1. Create empty chats for the IDs')
  console.log('2. Import chats from a JSON file')
  const option = await prompt('Choose an option (1/2): ')
  
  if (option === '1') {
    console.log('\nCreating empty chats for the specified IDs...')
    
    for (const chatId of chatIds) {
      // Create a simple chat object
      const chat = {
        id: chatId,
        title: 'Restored Chat',
        createdAt: new Date().toISOString(),
        userId: userId,
        path: `/chat/${chatId}`,
        messages: []
      }
      
      console.log(`Creating chat with ID: ${chatId}`)
      
      const { data, error } = await supabase
        .from('chats')
        .insert({
          id: chatId,
          user_id: userId,
          payload: chat
        })
        .select()
      
      if (error) {
        console.error(`Error creating chat ${chatId}:`, error)
      } else {
        console.log(`✅ Chat ${chatId} created successfully`)
      }
    }
  } else if (option === '2') {
    const filePath = await prompt('\nEnter the path to your JSON file containing chats: ')
    
    try {
      const fileData = fs.readFileSync(filePath, 'utf8')
      const chats = JSON.parse(fileData)
      
      console.log(`Found ${Array.isArray(chats) ? chats.length : 'non-array'} items in the file`)
      
      if (Array.isArray(chats)) {
        for (const chatData of chats) {
          // Extract chat data
          const chat = chatData.payload || chatData
          
          if (!chat || !chat.id) {
            console.error('Invalid chat data:', chatData)
            continue
          }
          
          console.log(`Importing chat with ID: ${chat.id}`)
          
          const { data, error } = await supabase
            .from('chats')
            .insert({
              id: chat.id,
              user_id: userId,
              payload: {
                ...chat,
                userId: userId // Ensure the chat has the correct user ID
              }
            })
            .select()
          
          if (error) {
            console.error(`Error importing chat ${chat.id}:`, error)
          } else {
            console.log(`✅ Chat ${chat.id} imported successfully`)
          }
        }
      } else {
        console.error('File does not contain a valid array of chats')
      }
    } catch (error) {
      console.error('Error reading or parsing file:', error)
    }
  } else {
    console.log('Invalid option selected')
  }
  
  console.log('\n===== Verification =====')
  console.log('Checking if chats exist in the database...')
  
  for (const chatId of chatIds) {
    const { data, error } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('id', chatId)
      .maybeSingle()
    
    if (error) {
      console.error(`Error checking chat ${chatId}:`, error)
    } else if (data) {
      console.log(`✅ Chat ${chatId} exists in the database`)
      console.log(`   Title: ${data.payload?.title}`)
      console.log(`   Messages: ${data.payload?.messages?.length || 0}`)
    } else {
      console.log(`❌ Chat ${chatId} not found in the database`)
    }
  }
  
  rl.close()
}

main().catch(error => {
  console.error('Unhandled error:', error)
  rl.close()
  process.exit(1)
}) 