'use client'

import * as React from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import Link from 'next/link'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import { SidebarList } from '@/components/sidebar-list'
import { SidebarFooter } from '@/components/sidebar-footer'
import { ThemeToggle } from '@/components/theme-toggle'
import { ClearHistory } from '@/components/clear-history'
import { UserMenu } from '@/components/user-menu'
import { RepositorySelector } from '@/components/repository-selector'
import { clearChats, createChat } from '@/app/actions'
import { useSidebar } from '@/lib/sidebar-context'
import { IconChevronLeft, IconChevronRight, IconPlus, IconSidebar } from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { toast } from 'react-hot-toast'
import { LoginButton } from '@/components/login-button'

export function CollapsibleSidebar() {
  const [session, setSession] = React.useState<any>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const supabase = createClientComponentClient()
  const { isExpanded, toggleSidebar } = useSidebar()
  const router = useRouter()
  const [isCreatingChat, setIsCreatingChat] = React.useState(false)
  
  React.useEffect(() => {
    const getSession = async () => {
      try {
        setIsLoading(true)
        const { data, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('Error getting session:', error)
          setSession(null)
        } else {
          setSession(data.session)
          console.log('Session user ID:', data.session?.user?.id)
        }
      } catch (err) {
        console.error('Failed to get session:', err)
        setSession(null)
      } finally {
        setIsLoading(false)
      }
    }
    
    getSession()
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      console.log('Auth state changed, user ID:', session?.user?.id)
      
      // If there's a session change, trigger a manual refresh
      if (session) {
        // Dispatch a custom event to force refresh of chats
        const event = new CustomEvent('session-changed', { detail: { id: session.user.id } })
        window.dispatchEvent(event)
      }
    })
    
    return () => subscription.unsubscribe()
  }, [supabase.auth])

  const handleNewChat = async () => {
    try {
      // Check if user is authenticated
      if (!session?.user) {
        toast.error('Please sign in to create a new chat')
        return
      }
      
      setIsCreatingChat(true)
      toast.loading('Creating new chat...')
      
      console.log('Creating new chat...')
      const result = await createChat()
      
      if ('error' in result) {
        toast.dismiss()
        toast.error(result.error)
        console.error('Failed to create chat:', result.error)
        return
      }
      
      console.log('Chat created with ID:', result.id)
      toast.dismiss()
      toast.success('New chat created')
      
      // Navigate to the new chat
      console.log('Navigating to new chat:', `/chat/${result.id}`)
      router.push(`/chat/${result.id}`)
      
      // Force a refresh to ensure everything is up to date
      setTimeout(() => {
        router.refresh()
        console.log('Router refreshed')
        
        // Also manually trigger a revalidation of the sidebar data
        const event = new CustomEvent('chat-created', { detail: { id: result.id } })
        window.dispatchEvent(event)
        console.log('chat-created event dispatched')
      }, 100)
    } catch (error) {
      console.error('Failed to create new chat:', error)
      toast.dismiss()
      toast.error('Failed to create new chat')
    } finally {
      setIsCreatingChat(false)
    }
  }
  
  return (
    <div className={cn(
      "group h-full transition-all duration-300 ease-in-out border-r bg-background",
      isExpanded ? "w-72 lg:w-80" : "w-16"
    )}>
      <div className="flex h-full flex-col">
        {/* Header with toggle button */}
        <div className="flex h-[52px] items-center justify-between px-2 py-2">
          {isExpanded ? (
            <>
              <div className="flex items-center px-2">
                <span className="font-semibold">Actuamind</span>
              </div>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={toggleSidebar} 
                className="h-8 w-8"
              >
                <IconChevronLeft className="h-4 w-4" />
                <span className="sr-only">Collapse Sidebar</span>
              </Button>
            </>
          ) : (
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={toggleSidebar} 
              className="h-8 w-8 mx-auto"
            >
              <IconChevronRight className="h-4 w-4" />
              <span className="sr-only">Expand Sidebar</span>
            </Button>
          )}
        </div>

        {/* New Chat Button */}
        <div className="px-2 py-2">
          {session?.user ? (
            <Button 
              variant="outline" 
              className={cn(
                "w-full justify-start gap-2",
                !isExpanded && "justify-center px-0"
              )}
              onClick={handleNewChat}
              disabled={isCreatingChat}
            >
              {isCreatingChat ? (
                <span className="animate-spin">⏳</span>
              ) : (
                <IconPlus className="h-4 w-4" />
              )}
              {isExpanded && <span>{isCreatingChat ? 'Creating...' : 'New Chat'}</span>}
            </Button>
          ) : (
            <div className={cn("flex justify-center", isExpanded && "px-2")}>
              {isExpanded ? (
                <LoginButton />
              ) : (
                <Button 
                  variant="outline" 
                  size="icon"
                  onClick={() => toast.error('Please sign in to create a new chat')}
                  className="h-8 w-8"
                >
                  <IconPlus className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}
        </div>
        
        {/* User and controls */}
        {isExpanded && (
          <div className="flex h-[52px] items-center justify-between px-4">
            <div className="flex items-center">
              {session?.user && <UserMenu user={session.user} />}
            </div>
            <div className="flex items-center justify-end space-x-2">
              <ThemeToggle />
              <ClearHistory clearChats={clearChats} />
            </div>
          </div>
        )}
        
        {/* Repository and chat list */}
        <div className={cn(
          "flex-1 overflow-auto",
          !isExpanded && "scrollbar-none"
        )}>
          {isExpanded ? (
            <>
              <RepositorySelector />
              <SidebarList userId={session?.user?.id} />
            </>
          ) : (
            <div className="flex flex-col items-center py-4 space-y-4">
              {session?.user && (
                <UserMenu user={session.user} compact={true} />
              )}
              <ThemeToggle compact={true} />
              <ClearHistory clearChats={clearChats} compact={true} />
            </div>
          )}
        </div>
        
        {/* Footer */}
        {isExpanded && <SidebarFooter />}
      </div>
    </div>
  )
} 