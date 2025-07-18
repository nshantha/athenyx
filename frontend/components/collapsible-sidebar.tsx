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
import { 
  IconChevronLeft, 
  IconChevronRight, 
  IconPlus, 
  IconSearch, 
  IconSidebar 
} from '@/components/ui/icons'
import { cn } from '@/lib/utils'
import { toast } from 'react-hot-toast'
import { LoginButton } from '@/components/login-button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { SearchDialog } from '@/components/search-dialog'

export function CollapsibleSidebar() {
  const [session, setSession] = React.useState<any>(null)
  const [isLoading, setIsLoading] = React.useState(true)
  const supabase = createClientComponentClient()
  const { isExpanded, toggleSidebar } = useSidebar()
  const router = useRouter()
  const [isCreatingChat, setIsCreatingChat] = React.useState(false)
  const [searchDialogOpen, setSearchDialogOpen] = React.useState(false)
  
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
  
  const handleSearch = () => {
    setSearchDialogOpen(true)
  };
  
  return (
    <>
      <SearchDialog 
        open={searchDialogOpen} 
        onOpenChange={setSearchDialogOpen} 
      />
      
      <div 
        className="group h-full transition-all duration-300 ease-in-out border-r bg-background fixed top-0 bottom-0 left-0 z-40 overflow-hidden"
        style={{ width: isExpanded ? '20rem' : '4rem' }}
      >
        {/* Create a CSS variable for sidebar width that can be accessed by other components */}
        <style jsx global>{`
          :root {
            --sidebar-width: ${isExpanded ? '20rem' : '4rem'};
          }
        `}</style>
        <div className="flex h-full flex-col">
          {/* Header with icons - fixed at top */}
          <div className="flex h-[52px] items-center justify-between px-2 py-2 shrink-0">
            {isExpanded ? (
              <>
                <div className="flex items-center gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={handleSearch}
                        className="h-8 w-8"
                      >
                        <IconSearch className="h-4 w-4" />
                        <span className="sr-only">Search</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>Search</p>
                    </TooltipContent>
                  </Tooltip>
                  
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        onClick={handleNewChat}
                        className="h-8 w-8"
                        disabled={isCreatingChat || !session?.user}
                      >
                        <IconPlus className="h-4 w-4" />
                        <span className="sr-only">New Chat</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>New Chat</p>
                    </TooltipContent>
                  </Tooltip>
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
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    onClick={toggleSidebar} 
                    className="h-8 w-8 mx-auto"
                  >
                    <IconChevronRight className="h-4 w-4" />
                    <span className="sr-only">Expand Sidebar</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Expand Sidebar</p>
                </TooltipContent>
              </Tooltip>
            )}
          </div>

          {/* Middle content area - scrollable */}
          <div className="flex-1 overflow-y-auto">
            {/* Repository management sections */}
            {isExpanded ? (
              <>
                {/* Repository selector with enhanced styling */}
                <RepositorySelector />
                
                {/* Chat list with separator */}
                <div className="px-4 py-2 mt-4 border-t border-border">
                  <div className="font-medium text-primary mb-2">Your chats</div>
                  <SidebarList userId={session?.user?.id} />
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center py-4 space-y-4">
                {/* Collapsed view items */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={handleSearch}
                      className="h-8 w-8 mx-auto mb-2"
                    >
                      <IconSearch className="h-4 w-4" />
                      <span className="sr-only">Search</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="right">
                    <p>Search</p>
                  </TooltipContent>
                </Tooltip>
                
                {session?.user ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button 
                        variant="outline" 
                        className="w-full justify-center px-0"
                        onClick={handleNewChat}
                        disabled={isCreatingChat}
                      >
                        {isCreatingChat ? (
                          <span className="animate-spin">⏳</span>
                        ) : (
                          <IconPlus className="h-4 w-4" />
                        )}
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="right">
                      <p>New Chat</p>
                    </TooltipContent>
                  </Tooltip>
                ) : (
                  <div className="flex justify-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button 
                          variant="outline" 
                          size="icon"
                          onClick={() => toast.error('Please sign in to create a new chat')}
                          className="h-8 w-8"
                        >
                          <IconPlus className="h-4 w-4" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="right">
                        <p>Sign in to create a new chat</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                )}
              </div>
            )}
          </div>
          
          {/* Footer with theme toggle and clear history */}
          {isExpanded ? (
            <div className="border-t border-border mt-auto">
              <SidebarFooter className="flex justify-end space-x-2">
                <ThemeToggle />
                <ClearHistory clearChats={clearChats} />
              </SidebarFooter>
            </div>
          ) : (
            <div className="mt-auto pb-4 pt-2 flex flex-col items-center space-y-4 border-t border-border">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <ThemeToggle compact={true} />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Toggle Theme</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <ClearHistory clearChats={clearChats} compact={true} />
                  </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Clear History</p>
                </TooltipContent>
              </Tooltip>
            </div>
          )}
        </div>
      </div>
    </>
  )
} 