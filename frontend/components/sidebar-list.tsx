'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useEffect, useState, useCallback } from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { toast } from 'react-hot-toast'
import { Database } from '@/lib/db_types'

import { cn } from '@/lib/utils'
import { IconMessage, IconTrash, IconEllipsis } from '@/components/ui/icons'
import { type Chat } from '@/lib/types'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

interface SidebarListProps {
  userId?: string
}

export function SidebarList({ userId }: SidebarListProps) {
  const [chats, setChats] = useState<Chat[]>([])
  const [lastFetch, setLastFetch] = useState<number>(0)
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const [authError, setAuthError] = useState<boolean>(false)
  const pathname = usePathname()
  const router = useRouter()
  const supabase = createClientComponentClient<Database>()

  // Create a memoized fetchChats function to avoid recreation on each render
  const fetchChats = useCallback(async (forceRefresh = false) => {
    if (!userId) {
      console.log('No userId provided, cannot fetch chats');
      setAuthError(true);
      return;
    }
    
    setAuthError(false);
    
    // Always log the fetch attempt for debugging
    console.log('Attempting to fetch chats from database, forceRefresh:', forceRefresh);
    console.log('Current userId:', userId, 'typeof:', typeof userId);
    
    // Implement debouncing - don't fetch if we just fetched within the last second
    // Unless forceRefresh is true
    const now = Date.now();
    if (!forceRefresh && now - lastFetch < 1000) {
      console.log('Skipping fetch, too soon after last fetch');
      return;
    }
    
    setLastFetch(now);
    
    try {
      // Check if the user is authenticated with a current session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      
      if (sessionError || !session) {
        console.error('Authentication error, user not logged in:', sessionError);
        setAuthError(true);
        return;
      }
      
      console.log('Fetching chats for user:', userId);
      console.log('Supabase client initialized:', !!supabase);
      
      // ONLY use the database query, don't fallback to localStorage
      const query = supabase
        .from('chats')
        .select('id, payload')
        .eq('user_id', userId)
        .order('payload->createdAt', { ascending: false });
      
      console.log('Query built, executing...');
      const { data, error } = await query;
      console.log('Query executed', data ? `with ${data.length} results` : 'with no results', error ? `Error: ${error.message}` : 'No error');

      if (error) {
        console.error('Error fetching chats:', error)
        toast.error('Failed to load chats')
        return
      }

      if (!data || data.length === 0) {
        console.log('No chats found for user in database');
        setChats([]);
        return;
      }

      // Process the data to ensure we have correct information
      const chatData = data.map(entry => {
        // Get the payload data
        const chat = entry.payload as Chat;
        
        // IMPORTANT: Make sure the chat ID matches the database record ID
        if (chat.id !== entry.id) {
          console.log(`Correcting ID mismatch: payload.id=${chat.id}, database.id=${entry.id}`);
          chat.id = entry.id;
        }
        
        // Ensure chat path is correct
        chat.path = `/chat/${entry.id}`;
        
        console.log(`Chat: DB ID=${entry.id}, Title="${chat.title}"`);
        
        return chat;
      }) || []
      
      console.log('Fetched chats from database:', chatData.length);
      
      // Always update the state with fresh data from database
      setChats(chatData);
      
    } catch (error) {
      console.error('Error fetching chats from database:', error)
      toast.error('Failed to load chats')
    }
  }, [userId, supabase, lastFetch])

  // Handle chat deletion
  const handleDeleteChat = async (chat: Chat) => {
    if (!userId || isDeleting) return;
    
    setIsDeleting(chat.id);
    try {
      const { error } = await supabase
        .from('chats')
        .delete()
        .eq('id', chat.id);
      
      if (error) {
        console.error('Error deleting chat:', error);
        toast.error('Failed to delete chat');
        return;
      }
      
      // Update local state immediately for responsive UI
      setChats(prev => prev.filter(c => c.id !== chat.id));
      
      // If we're currently viewing this chat, redirect to home
      if (pathname === `/chat/${chat.id}`) {
        router.push('/');
      }
      
      toast.success('Chat deleted');
    } catch (error) {
      console.error('Error in handleDeleteChat:', error);
      toast.error('Failed to delete chat');
    } finally {
      setIsDeleting(null);
    }
  };

  // Fetch chats when the component mounts or userId changes
  useEffect(() => {
    if (!userId) {
      setChats([])
      return
    }

    // Force refresh on initial mount - only use database
    console.log('Initial mount of SidebarList, fetching chats from database for user:', userId);
    fetchChats(true)
    
    // Also set up a periodic refresh every 5 seconds to ensure we have the latest data
    const intervalId = setInterval(() => {
      console.log('Periodic refresh of chats from database');
      fetchChats(true);
    }, 5000);

    // Subscribe to changes in the database
    const channel = supabase
      .channel('chats-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'chats',
          filter: `user_id=eq.${userId}`
        },
        (payload) => {
          console.log('Received database chat update:', payload.eventType, payload);
          // Force refresh for any database change
          fetchChats(true);
        }
      )
      .subscribe()
      
    // Listen for the custom chat-created event
    const handleChatCreated = (event: any) => {
      console.log('Chat created event received with detail:', event.detail);
      fetchChats(true); // Force refresh to ensure we get the latest data from the database
    };
    
    // Listen for session changes
    const handleSessionChanged = (event: any) => {
      console.log('Session changed event received with detail:', event.detail);
      fetchChats(true); // Force refresh to ensure we get the latest data from the database
    };
    
    window.addEventListener('chat-created', handleChatCreated);
    window.addEventListener('session-changed', handleSessionChanged);

    return () => {
      clearInterval(intervalId);
      supabase.removeChannel(channel);
      window.removeEventListener('chat-created', handleChatCreated);
      window.removeEventListener('session-changed', handleSessionChanged);
    }
  }, [userId, supabase, fetchChats])

  if (!userId) {
    return (
      <div className="p-8 text-center">
        <p className="text-sm text-muted-foreground">Please sign in to view chats</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto">
      {chats.length > 0 ? (
        <div className="space-y-2 px-2">
          <h2 className="px-2 text-lg font-semibold">Your chats</h2>
          {chats.map(chat => {
            // Determine chat title - use first user message if title is still "New Chat"
            let displayTitle = chat.title
            if (displayTitle === 'New Chat' && chat.messages && chat.messages.length > 0) {
              const firstUserMessage = chat.messages.find(m => m.role === 'user')
              if (firstUserMessage) {
                displayTitle = firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '')
              }
            }
            
            // Get database ID (for debugging display)
            const dbId = chat.id;
            
            return (
              <div 
                key={dbId}
                className={cn(
                  'flex items-center justify-between rounded-lg px-2 py-1 hover:bg-accent',
                  pathname === `/chat/${dbId}` && 'bg-accent'
                )}
                onClick={() => console.log('Chat item clicked. ID:', dbId, 'Path:', `/chat/${dbId}`)}
              >
                <Link
                  href={`/chat/${dbId}`}
                  className="flex items-center gap-2 flex-1 min-w-0"
                  onClick={(e) => {
                    console.log('Chat link clicked. Using database ID:', dbId);
                  }}
                >
                  <IconMessage className="h-4 w-4 shrink-0" />
                  <div className="flex-1 truncate">
                    {displayTitle || 'New Chat'}
                  </div>
                </Link>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button 
                      className="h-7 w-7 rounded-md p-0 hover:bg-accent-foreground/10 flex items-center justify-center"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <IconEllipsis className="h-4 w-4" />
                      <span className="sr-only">Chat options</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      className="text-destructive focus:text-destructive flex items-center gap-2"
                      onClick={() => handleDeleteChat(chat)}
                      disabled={isDeleting === chat.id}
                    >
                      {isDeleting === chat.id ? (
                        <span className="animate-spin">⏳</span>
                      ) : (
                        <IconTrash className="h-4 w-4" />
                      )}
                      Delete
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="p-8 text-center">
          {authError ? (
            <>
              <p className="text-sm text-muted-foreground mb-2">Authentication error</p>
              <p className="text-xs text-muted-foreground mb-4">Please sign in again to view your chats</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground mb-2">No chat history</p>
          )}
          <button 
            onClick={() => fetchChats(true)} 
            className="text-xs text-blue-600 hover:underline"
          >
            Refresh chats
          </button>
        </div>
      )}
    </div>
  )
}
