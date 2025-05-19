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
    <div className="flex items-center justify-between">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className={cn("pl-0", compact && "p-0 h-auto")}>
            {user?.user_metadata.avatar_url ? (
              <Image
                height={60}
                width={60}
                className={cn(
                  "select-none rounded-full ring-1 ring-zinc-100/10 transition-opacity duration-300 hover:opacity-80",
                  compact ? "h-8 w-8" : "h-6 w-6"
                )}
                src={getAvatarUrl()}
                alt={user.user_metadata.name ?? 'Avatar'}
              />
            ) : (
              <div className={cn(
                "flex shrink-0 select-none items-center justify-center rounded-full bg-muted/50 text-xs font-medium uppercase text-muted-foreground",
                compact ? "h-8 w-8" : "h-7 w-7"
              )}>
                {getUserInitials(user?.user_metadata.name ?? user?.email)}
              </div>
            )}
            {!compact && <span className="ml-2">{user?.user_metadata.name ?? '👋🏼'}</span>}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent sideOffset={8} align="start" className="w-[180px]">
          <DropdownMenuItem className="flex-col items-start">
            <div className="text-xs font-medium">
              {user?.user_metadata.name}
            </div>
            <div className="text-xs text-zinc-500">{user?.email}</div>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <a
              href="/profile"
              className="inline-flex w-full items-center justify-between text-xs"
            >
              Profile Settings
              <IconExternalLink className="ml-auto h-3 w-3" />
            </a>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={signOut} className="text-xs">
            Log Out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
