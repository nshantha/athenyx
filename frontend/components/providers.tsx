'use client'

import { ThemeProvider as NextThemesProvider } from 'next-themes'
import { ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'
import { RepositoryProvider } from '@/lib/repository-context'
import { TooltipProvider } from '@/components/ui/tooltip'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <NextThemesProvider attribute="class" defaultTheme="dark">
      <RepositoryProvider>
        <TooltipProvider>
          <Toaster />
          {children}
        </TooltipProvider>
      </RepositoryProvider>
    </NextThemesProvider>
  )
}
