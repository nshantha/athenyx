import { Metadata } from 'next'

import { Toaster } from 'react-hot-toast'

import '@/app/globals.css'
import { fontMono, fontSans } from '@/lib/fonts'
import { cn } from '@/lib/utils'
import { TailwindIndicator } from '@/components/tailwind-indicator'
import { Providers } from '@/components/providers'
import { Header } from '@/components/header'
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
            {/* Persistent left navigation sidebar for desktop */}
            <div className="hidden md:block md:w-72 lg:w-80 flex-shrink-0 border-r bg-background">
              <div className="fixed h-full w-72 lg:w-80 overflow-y-auto">
                <ClientSidebar />
              </div>
            </div>
            
            {/* Main content */}
            <div className="flex flex-col flex-1">
              {/* @ts-ignore */}
              <Header />
              <main className="flex flex-1 flex-col bg-muted/50">{children}</main>
            </div>
          </div>
          <TailwindIndicator />
        </Providers>
      </body>
    </html>
  )
}
