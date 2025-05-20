import { Metadata } from 'next'

import { Toaster } from 'react-hot-toast'

import '@/app/globals.css'
import { fontMono, fontSans } from '@/lib/fonts'
import { cn } from '@/lib/utils'
import { TailwindIndicator } from '@/components/tailwind-indicator'
import { Providers } from '@/components/providers'
import { MainContent } from '@/components/main-content'
import ClientSidebar from '@/components/client-sidebar'

export const metadata: Metadata = {
  title: {
    default: 'Actuamind Code Explorer',
    template: `%s - Actuamind Code Explorer`
  },
  description: 'An AI-powered code exploration tool built with Next.js.',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' }
  ],
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon-16x16.png',
    apple: '/apple-touch-icon.png'
  }
}

interface RootLayoutProps {
  children: React.ReactNode
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head />
      <body
        className={cn(
          'font-sans antialiased',
          fontSans.variable,
          fontMono.variable
        )}
      >
        <Toaster />
        <Providers>
          <div className="flex min-h-screen">
            {/* Sidebar - now handled by the CollapsibleSidebar component */}
            <div className="hidden md:block">
              <ClientSidebar />
            </div>
            
            {/* Main content with dynamic margin */}
            <MainContent>{children}</MainContent>
          </div>
          <TailwindIndicator />
        </Providers>
      </body>
    </html>
  )
}


