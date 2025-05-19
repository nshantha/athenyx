'use client'

import * as React from 'react'
import { useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

interface LogoLinkProps {
  children: React.ReactNode
}

export function LogoLink({ children }: LogoLinkProps) {
  const pathname = usePathname()
  const router = useRouter()
  const [isNavigating, setIsNavigating] = useState(false)
  
  const handleLogoClick = async (e: React.MouseEvent) => {
    e.preventDefault()
    
    if (isNavigating) return
    setIsNavigating(true)
    
    try {
      console.log('Logo clicked, current pathname:', pathname)
      
      // Force navigation to home page regardless of current path
      router.push('/')
      
      // For good measure, also replace the current history entry
      // This helps prevent history stack issues
      setTimeout(() => {
        router.replace('/')
      }, 50)
      
      console.log('Navigation to home triggered')
    } catch (err) {
      console.error('Error navigating to home:', err)
    } finally {
      // Reset the navigating state after a delay
      setTimeout(() => setIsNavigating(false), 300)
    }
  }
  
  return (
    <a 
      href="/" 
      onClick={handleLogoClick} 
      className={cn(
        "flex items-center transition-all duration-200",
        isNavigating ? "opacity-70 pointer-events-none" : "hover:opacity-80"
      )}
      aria-label="Go to Home"
    >
      {children}
      {isNavigating && (
        <span className="ml-2 animate-pulse">•</span>
      )}
    </a>
  )
} 