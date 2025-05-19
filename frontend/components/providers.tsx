'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'
import { ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'
import { RepositoryProvider } from '@/lib/repository-context'
import { SidebarProvider } from '@/lib/sidebar-context'
import { TooltipProvider } from '@/components/ui/tooltip'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="dark">
      <RepositoryProvider>
        <SidebarProvider>
          <TooltipProvider>
            <Toaster />
            {children}
          </TooltipProvider>
        </SidebarProvider>
      </RepositoryProvider>
    </NextThemesProvider>
  )
}
