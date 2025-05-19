// Script to check database schema and test queries
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

async function main() {
  try {
    console.log('===== Database Schema and Query Check =====\n')
    
    // Step 1: Get all tables in the public schema
    console.log('Step 1: Checking tables in the public schema...')
    
    let tables = null;
    let tablesError = null;
    
    try {
      const response = await supabase.rpc('list_tables');
      tables = response.data;
      tablesError = response.error;
    } catch (err) {
      tablesError = { message: 'Function not available' };
    }
    
    if (tablesError) {
      console.error('Error getting tables:', tablesError)
      
      // Alternative query if rpc is not available
      console.log('Trying alternative approach...')
      const { data: tableData, error: tableError } = await supabase
        .from('chats')
        .select('*')
        .limit(1)
      
      if (tableError) {
        console.error('Error checking tables:', tableError)
      } else {
        console.log('Chats table exists and is accessible')
      }
    } else {
      console.log('Tables in public schema:', tables)
    }
    
    // Step 2: Check the structure of the chats table
    console.log('\nStep 2: Checking chats table structure...')
    const { data: chatsInfo, error: structError } = await supabase
      .from('chats')
      .select('*')
      .limit(1)
    
    if (structError) {
      console.error('Error getting chats structure:', structError)
    } else {
      if (chatsInfo && chatsInfo.length > 0) {
        const sampleChat = chatsInfo[0]
        console.log('Chats table columns:', Object.keys(sampleChat))
        console.log('Sample chat data structure:', JSON.stringify(sampleChat, null, 2))
      } else {
        console.log('No chats found to analyze structure')
      }
    }
    
    // Step 3: Try different query patterns
    console.log('\nStep 3: Testing various query patterns...')
    
    // Get current user first (optional)
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    const userId = user?.id
    
    console.log('Current authenticated user:', userId || 'None')
    
    // Query 1: Fetch all chats
    console.log('\nQuery 1: Fetching all chats...')
    const { data: allChats, error: allChatsError } = await supabase
      .from('chats')
      .select('*')
      .limit(10)
    
    if (allChatsError) {
      console.error('Error fetching all chats:', allChatsError)
    } else {
      console.log(`Found ${allChats?.length || 0} chats in total`)
      
      if (allChats && allChats.length > 0) {
        console.log('First chat sample:', {
          id: allChats[0].id,
          user_id: allChats[0].user_id,
          payload_type: typeof allChats[0].payload,
          has_payload: !!allChats[0].payload
        })
      }
    }
    
    // Query 2: Fetch chats by user_id
    if (userId) {
      console.log('\nQuery 2: Fetching chats for current user...')
      const { data: userChats, error: userChatsError } = await supabase
        .from('chats')
        .select('*')
        .eq('user_id', userId)
        .limit(10)
      
      if (userChatsError) {
        console.error('Error fetching user chats:', userChatsError)
      } else {
        console.log(`Found ${userChats?.length || 0} chats for user ${userId}`)
      }
    } else {
      console.log('\nQuery 2: Skipped (no authenticated user)')
    }
    
    // Query 3: Test advanced query with JSON field filtering
    console.log('\nQuery 3: Testing payload JSON field query...')
    const { data: jsonQueryData, error: jsonQueryError } = await supabase
      .from('chats')
      .select('id, user_id, payload')
      .order('payload->createdAt', { ascending: false })
      .limit(5)
    
    if (jsonQueryError) {
      console.error('Error with JSON field query:', jsonQueryError)
    } else {
      console.log(`JSON field query returned ${jsonQueryData?.length || 0} results`)
    }
    
    // Query 4: Check specific ID
    console.log('\nQuery 4: Testing fetch by specific ID...')
    // Random test ID - replace with an actual ID from your database if available
    const testId = allChats && allChats.length > 0 ? allChats[0].id : 'test-id'
    
    const { data: idData, error: idError } = await supabase
      .from('chats')
      .select('*')
      .eq('id', testId)
      .maybeSingle()
    
    if (idError) {
      console.error('Error fetching by ID:', idError)
    } else {
      console.log(`ID query for "${testId}" returned:`, idData ? 'record found' : 'no record')
    }
    
    // Query 5: Test ID search in payload
    console.log('\nQuery 5: Testing payload ID search...')
    const { data: payloadIdData, error: payloadIdError } = await supabase
      .from('chats')
      .select('*')
      .filter('payload->>id', 'eq', testId)
      .maybeSingle()
    
    if (payloadIdError) {
      console.error('Error with payload ID search:', payloadIdError)
    } else {
      console.log(`Payload ID search for "${testId}" returned:`, payloadIdData ? 'record found' : 'no record')
    }
    
    // Write results to file for detailed analysis
    const report = {
      timestamp: new Date().toISOString(),
      tables,
      sampleChat: chatsInfo && chatsInfo.length > 0 ? chatsInfo[0] : null,
      allChatsCount: allChats?.length || 0,
      queries: {
        byId: { success: !idError, result: idData ? 'found' : 'not found' },
        byPayloadId: { success: !payloadIdError, result: payloadIdData ? 'found' : 'not found' },
        byJsonField: { success: !jsonQueryError, resultCount: jsonQueryData?.length || 0 }
      }
    }
    
    fs.writeFileSync('db-schema-report.json', JSON.stringify(report, null, 2))
    console.log('\nDetailed report written to db-schema-report.json')
    
  } catch (error) {
    console.error('Unhandled error:', error)
  }
}

main() 