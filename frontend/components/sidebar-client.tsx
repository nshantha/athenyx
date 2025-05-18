'use client'

import * as React from 'react'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger
} from '@/components/ui/sheet'
import { IconSidebar } from '@/components/ui/icons'
import { SidebarList } from '@/components/sidebar-list'
import { SidebarFooter } from '@/components/sidebar-footer'
import { ThemeToggle } from '@/components/theme-toggle'
import { ClearHistory } from '@/components/clear-history'
import { UserMenu } from '@/components/user-menu'
import { RepositorySelector } from '@/components/repository-selector'
import { clearChats } from '@/app/actions'

// This is the client version of the sidebar components
// These are exported separately to allow dynamic import without .then()

export default function SidebarDesktopClient() {
  const [session, setSession] = React.useState<any>(null)
  const supabase = createClientComponentClient()
  
  React.useEffect(() => {
    const getSession = async () => {
      const { data } = await supabase.auth.getSession()
      setSession(data.session)
    }
    
    getSession()
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    
    return () => subscription.unsubscribe()
  }, [supabase.auth])
  
  return (
    <div className="group w-full overflow-hidden">
      <div className="flex h-full flex-col bg-background px-2">
        <div className="flex h-[52px] items-center justify-between px-4">
          <div className="flex items-center">
            {session?.user && <UserMenu user={session.user} />}
          </div>
          <div className="flex items-center justify-end space-x-2">
            <ThemeToggle />
            <ClearHistory clearChats={clearChats} />
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          <RepositorySelector />
          <SidebarList userId={session?.user?.id} />
        </div>
        <SidebarFooter />
      </div>
    </div>
  )
}

// For Sheet sidebar
export function SidebarClient({ children }: { children: React.ReactNode }) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        {children || (
          <Button variant="ghost" className="-ml-2 h-9 w-9 p-0">
            <IconSidebar className="h-6 w-6" />
            <span className="sr-only">Toggle Sidebar</span>
          </Button>
        )}
      </SheetTrigger>
      <SheetContent className="inset-y-0 flex h-auto w-[300px] flex-col p-0">
        <SheetHeader className="p-4">
          <SheetTitle className="text-sm">Repository & Chat History</SheetTitle>
        </SheetHeader>
        <SidebarMobileClient />
      </SheetContent>
    </Sheet>
  )
}

// Mobile sidebar component
export function SidebarMobileClient() {
  const [session, setSession] = React.useState<any>(null)
  const supabase = createClientComponentClient()
  
  React.useEffect(() => {
    const getSession = async () => {
      const { data } = await supabase.auth.getSession()
      setSession(data.session)
    }
    
    getSession()
    
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
    })
    
    return () => subscription.unsubscribe()
  }, [supabase.auth])
  
  return (
    <div className="group w-full overflow-hidden">
      <div className="flex h-full flex-col bg-background">
        <div className="flex h-[52px] items-center justify-between px-4">
          <div className="flex items-center">
            {session?.user && <UserMenu user={session.user} />}
          </div>
          <div className="flex items-center justify-end space-x-2">
            <ThemeToggle />
            <ClearHistory clearChats={clearChats} />
          </div>
        </div>
        <div className="flex-1 overflow-auto">
          <RepositorySelector />
          <SidebarList userId={session?.user?.id} />
        </div>
        <SidebarFooter />
      </div>
    </div>
  )
} 