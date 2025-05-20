'use client'

import { useSidebar } from '@/lib/sidebar-context'
import { cn } from '@/lib/utils'
import { HeaderClient } from '@/components/header-client'

export function MainContent({ children }: { children: React.ReactNode }) {
  const { isExpanded } = useSidebar()
  
  return (
    <div className={cn(
      "flex flex-col flex-1 transition-all duration-300 ease-in-out",
      isExpanded ? "md:ml-72 lg:ml-80" : "md:ml-16"
    )}>
      <HeaderClient />
      <main className="flex flex-1 flex-col bg-muted/50">{children}</main>
    </div>
  )
} 