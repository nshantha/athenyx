'use client'

import Image from 'next/image'
import { type Session } from '@supabase/auth-helpers-nextjs'
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { IconExternalLink } from '@/components/ui/icons'
import { CiSettings } from "react-icons/ci"
import { RiRobot2Line } from "react-icons/ri"
import { BsPlug } from "react-icons/bs"
import { cn } from '@/lib/utils'

export interface UserMenuProps {
  user: Session['user']
  compact?: boolean
}

function getUserInitials(name: string) {
  const [firstName, lastName] = name.split(' ')
  return lastName ? `${firstName[0]}${lastName[0]}` : firstName.slice(0, 2)
}

export function UserMenu({ user, compact = false }: UserMenuProps) {
  const router = useRouter()

  // Create a Supabase client configured to use cookies
  const supabase = createClientComponentClient()

  const signOut = async () => {
    await supabase.auth.signOut()
    router.refresh()
  }

  // Function to get the correct avatar URL based on provider
  const getAvatarUrl = () => {
    if (!user?.user_metadata.avatar_url) return ''
    
    // For Google URLs, don't append size parameter
    if (user.app_metadata.provider === 'google') {
      return user.user_metadata.avatar_url
    }
    
    // For other providers like GitHub, append size parameter
    return `${user.user_metadata.avatar_url}&s=60`
  }

  return (
    <div className="inline-flex">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="p-0 h-8 w-8 rounded-full hover:bg-transparent">
            {user?.user_metadata.avatar_url ? (
              <Image
                height={32}
                width={32}
                className="h-8 w-8 select-none rounded-full ring-1 ring-border transition-opacity duration-300 hover:opacity-80"
                src={getAvatarUrl()}
                alt={user.user_metadata.name ?? 'Avatar'}
              />
            ) : (
              <div className="h-8 w-8 flex shrink-0 select-none items-center justify-center rounded-full bg-muted text-xs font-medium uppercase text-muted-foreground"> {/* Changed bg-muted/50 to bg-muted for consistency */}
                {getUserInitials(user?.user_metadata.name ?? user?.email)}
              </div>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent sideOffset={8} align="end" className="w-[180px] bg-card border-border shadow-lg"> {/* Ensured card background and border */}
          <DropdownMenuItem className="flex-col items-start focus:bg-muted"> {/* Added focus style */}
            <div className="text-xs font-medium text-foreground"> {/* Ensured foreground color */}
              {user?.user_metadata.name}
            </div>
            <div className="text-xs text-muted-foreground">{user?.email}</div> {/* Changed to muted-foreground */}
          </DropdownMenuItem>
          <DropdownMenuSeparator className="bg-border" /> {/* Ensured separator uses border color */}
          <DropdownMenuItem asChild>
            <a
              href="/settings"
              className="inline-flex w-full items-center justify-between text-xs text-foreground hover:bg-muted focus:bg-muted" // Added text/hover/focus styles
            >
              <div className="flex items-center">
                <CiSettings className="mr-2 h-4 w-4 text-muted-foreground" /> {/* Icon color */}
                Profile Settings
              </div>
              <IconExternalLink className="ml-auto h-3 w-3 text-muted-foreground" /> {/* Icon color */}
            </a>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <a
              href="/workflow"
              className="inline-flex w-full items-center justify-between text-xs text-foreground hover:bg-muted focus:bg-muted" // Added text/hover/focus styles
            >
              <div className="flex items-center">
                <RiRobot2Line className="mr-2 h-4 w-4 text-muted-foreground" /> {/* Icon color */}
                Workflows
              </div>
              <IconExternalLink className="ml-auto h-3 w-3 text-muted-foreground" /> {/* Icon color */}
            </a>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <a
              href="/integrations"
              className="inline-flex w-full items-center justify-between text-xs text-foreground hover:bg-muted focus:bg-muted" // Added text/hover/focus styles
            >
              <div className="flex items-center">
                <BsPlug className="mr-2 h-4 w-4 text-muted-foreground" /> {/* Icon color */}
                Integrations
              </div>
              <IconExternalLink className="ml-auto h-3 w-3 text-muted-foreground" /> {/* Icon color */}
            </a>
          </DropdownMenuItem>
          <DropdownMenuSeparator className="bg-border" /> {/* Ensured separator uses border color */}
          <DropdownMenuItem onClick={signOut} className="text-xs text-foreground hover:bg-muted focus:bg-muted cursor-pointer"> {/* Added styles and cursor */}
            Log Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
