'use client'

import React from 'react'
import { Sidebar } from '@/components/sidebar'
import { Button } from '@/components/ui/button'
import { IconSidebar } from '@/components/ui/icons'

export default function MobileSidebar() {
  return (
    <Sidebar>
      <Button variant="ghost" className="h-9 w-9 p-0">
        <IconSidebar className="h-6 w-6" />
        <span className="sr-only">Toggle Sidebar</span>
      </Button>
    </Sidebar>
  )
} 