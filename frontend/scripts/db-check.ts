// This script checks the database for chat data
import { createClient } from '@supabase/supabase-js'
import dotenv from 'dotenv'
import fs from 'fs'

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

// List of chat IDs to check
const chatIds = [
  '2f8ff17c-19e6-4c7a-a369-27f23d48bbd3',
  '7ac0def5-d9ef-42f9-9b9d-076b36e8d1f5',
  'abb15092-27fe-40d6-9d18-497fa527c7de',
  'ecb548c3-317b-4507-bddb-3f154e921b53'
]

async function main() {
  console.log('Checking database connection...')
  
  // Check if we can access the database
  const { data: tablesData, error: tablesError } = await supabase
    .from('chats')
    .select('count')
    .limit(1)
  
  if (tablesError) {
    console.error('Error accessing database:', tablesError)
    process.exit(1)
  }
  
  console.log('Database connection successful\n')
  
  // Get all chats
  const { data: allChats, error: allChatsError } = await supabase
    .from('chats')
    .select('id, user_id, payload, created_at')
    .order('created_at', { ascending: false })
    .limit(10)
  
  if (allChatsError) {
    console.error('Error fetching chats:', allChatsError)
  } else {
    console.log(`Found ${allChats?.length || 0} total chats\n`)
    
    // Print summary of all chats
    console.log('Summary of all chats:')
    allChats?.forEach((chat, index) => {
      console.log(`${index + 1}. ID: ${chat.id}, User: ${chat.user_id}`)
      console.log(`   Payload ID: ${chat.payload?.id}`)
      console.log(`   Title: ${chat.payload?.title}`)
      console.log(`   Messages: ${chat.payload?.messages?.length || 0}`)
      console.log(`   Created: ${chat.created_at}`)
      console.log('---')
    })
    
    // Write detailed data to a file
    fs.writeFileSync('chat-data.json', JSON.stringify(allChats, null, 2))
    console.log('\nDetailed data written to chat-data.json')
  }
  
  // Check each specific chat ID
  console.log('\nChecking specific chat IDs:')
  for (const chatId of chatIds) {
    console.log(`\nLooking for chat with ID: ${chatId}`)
    
    // Try by record ID
    const { data: byRecordId, error: recordError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .eq('id', chatId)
      .maybeSingle()
    
    if (recordError) {
      console.error(`Error searching by record ID for ${chatId}:`, recordError)
    } else if (byRecordId) {
      console.log('✅ Found by record ID!')
      console.log(`  User: ${byRecordId.user_id}`)
      console.log(`  Payload ID: ${byRecordId.payload?.id}`)
      console.log(`  Title: ${byRecordId.payload?.title}`)
    } else {
      console.log('❌ Not found by record ID')
    }
    
    // Try by payload ID
    const { data: byPayloadId, error: payloadError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .filter('payload->>id', 'eq', chatId)
      .maybeSingle()
    
    if (payloadError) {
      console.error(`Error searching by payload ID for ${chatId}:`, payloadError)
    } else if (byPayloadId) {
      console.log('✅ Found by payload ID!')
      console.log(`  DB Record ID: ${byPayloadId.id}`)
      console.log(`  User: ${byPayloadId.user_id}`)
      console.log(`  Title: ${byPayloadId.payload?.title}`)
    } else {
      console.log('❌ Not found by payload ID')
    }
  }
}

main().catch(error => {
  console.error('Unhandled error:', error)
  process.exit(1)
}) 