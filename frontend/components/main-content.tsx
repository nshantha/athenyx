'use client'

import { useSidebar } from '@/lib/sidebar-context'
import { cn } from '@/lib/utils'
import { HeaderClient } from '@/components/header-client'

export function MainContent({ children }: { children: React.ReactNode }) {
  // const { isExpanded } = useSidebar() // isExpanded is not directly used here anymore
  
  // The marginLeft is now directly controlled by the --sidebar-width CSS variable,
  // which is updated by the CollapsibleSidebar component.
  // The transition-all class handles the smooth animation.
  
  return (
    <div 
      className="flex flex-col flex-1 transition-all duration-300 ease-in-out w-full"
      style={{ marginLeft: 'var(--sidebar-width)' }}
    >
      <HeaderClient />
      <main className="flex flex-1 flex-col bg-muted/50 overflow-auto">{children}</main>
    </div>
  )
} 