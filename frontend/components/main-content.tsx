'use client'

import { useSidebar } from '@/lib/sidebar-context'
import { cn } from '@/lib/utils'
import { HeaderClient } from '@/components/header-client'

export function MainContent({ children }: { children: React.ReactNode }) {
  const { isExpanded } = useSidebar()
  
  // Calculate the proper margin based on sidebar state
  const getContentMargin = () => {
    return isExpanded ? '20rem' : '4rem';
  };
  
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