'use client'

import * as React from 'react'
import Link from 'next/link'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { IconNextChat } from '@/components/ui/icons'
import { UserMenu } from '@/components/user-menu'
import MobileSidebar from '@/components/mobile-sidebar'
import { LogoLink } from '@/components/logo-link'
import { CiSettings } from 'react-icons/ci'
import { RiRobot2Line } from 'react-icons/ri'
import { BsPlug } from 'react-icons/bs'

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
    <>
      <style jsx global>{`
        .relative:hover .tooltip {
          opacity: 1 !important;
          transition: none !important;
          visibility: visible !important;
        }
        .tooltip {
          transition: none !important;
          visibility: hidden;
          z-index: 100;
        }
      `}</style>
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
      </div>

      <div className="flex items-center justify-end">
        {session?.user ? (
          <div className="flex items-center space-x-5">
            <div className="relative">
              <Link 
                href="/workflow" 
                className="text-foreground hover:text-primary transition-colors flex items-center justify-center"
                aria-label="Workflows"
              >
                <RiRobot2Line className="h-6 w-6" />
              </Link>
              <div className="tooltip absolute top-full left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-gray-800 text-white text-xs rounded px-2 py-1 pointer-events-none mt-1 shadow-md">Workflows</div>
            </div>
            <div className="relative">
              <Link 
                href="/integrations" 
                className="text-foreground hover:text-primary transition-colors flex items-center justify-center"
                aria-label="Integrations"
              >
                <BsPlug className="h-6 w-6" />
              </Link>
              <div className="tooltip absolute top-full left-1/2 transform -translate-x-1/2 whitespace-nowrap bg-gray-800 text-white text-xs rounded px-2 py-1 pointer-events-none mt-1 shadow-md">Integrations</div>
            </div>
            <span className="mx-3 text-muted-foreground/50">|</span>
            <UserMenu user={session.user} />
          </div>
        ) : (
          <Button variant="link" asChild>
            <Link href="/sign-in">Login</Link>
          </Button>
        )}
      </div>
      </header>
    </>
  )
}
