'use client'

import * as React from 'react'
import Link from 'next/link'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { IconNextChat, IconSeparator, IconSidebar } from '@/components/ui/icons'
import { UserMenu } from '@/components/user-menu'
import MobileSidebar from '@/components/mobile-sidebar'
import { LogoLink } from '@/components/logo-link'

export function HeaderClient() {
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
    <header className="sticky top-0 z-50 flex h-16 w-full shrink-0 items-center justify-between border-b bg-gradient-to-b from-background/10 via-background/50 to-background/80 px-4 backdrop-blur-xl">
      <div className="flex items-center">
        {/* Mobile Sidebar Trigger - Client Component */}
        <div className="md:hidden mr-2">
          <MobileSidebar />
        </div>
        
        <LogoLink>
          <IconNextChat className="mr-2 h-6 w-6 dark:hidden" inverted />
          <IconNextChat className="mr-2 hidden h-6 w-6 dark:block" />
          <span className="font-bold text-lg">Actuamind</span>
        </LogoLink>
        
        <div className="flex items-center ml-4">
          <IconSeparator className="h-6 w-6 text-muted-foreground/50" />
          {session?.user ? (
            <UserMenu user={session.user} />
          ) : (
            <Button variant="link" asChild className="-ml-2">
              <Link href="/sign-in">Login</Link>
            </Button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-end space-x-2">
      </div>
    </header>
  )
} 