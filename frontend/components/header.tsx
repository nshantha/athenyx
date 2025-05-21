import * as React from 'react'
import Link from 'next/link'

import { cn } from '@/lib/utils'
import { auth } from '@/auth'
import { Button } from '@/components/ui/button'
import { IconNextChat, IconSeparator, IconSidebar } from '@/components/ui/icons'
import { UserMenu } from '@/components/user-menu'
import { cookies } from 'next/headers'
import MobileSidebar from '@/components/mobile-sidebar'
import { LogoLink } from '@/components/logo-link'
import { CiSettings } from 'react-icons/ci'
import { RiRobot2Line } from 'react-icons/ri'
import { BsPlug } from 'react-icons/bs'

export async function Header() {
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
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
      </div>
      <div className="flex items-center justify-end">
        {session?.user && (
          <div className="flex items-center space-x-5">
            <Link 
              href="/workflow" 
              className="text-foreground hover:text-primary transition-colors"
              aria-label="Workflows"
            >
              <RiRobot2Line className="h-6 w-6" />
            </Link>
            <Link 
              href="/integrations" 
              className="text-foreground hover:text-primary transition-colors"
              aria-label="Integrations"
            >
              <BsPlug className="h-6 w-6" />
            </Link>
            <span className="mx-3 text-muted-foreground/50">|</span>
            <UserMenu user={session.user} />
          </div>
        )}
        {!session?.user && (
          <Button variant="link" asChild>
            <Link href="/sign-in">Login</Link>
          </Button>
        )}
      </div>
    </header>
  )
}
