'use client'

import * as React from 'react'
import { useInView } from 'react-intersection-observer'

import { useAtBottom } from '@/lib/hooks/use-at-bottom'

interface ChatScrollAnchorProps {
  trackVisibility?: boolean
}

export function ChatScrollAnchor({ trackVisibility }: ChatScrollAnchorProps) {
  const isAtBottom = useAtBottom()
  const { ref, entry, inView } = useInView({
    trackVisibility,
    delay: 100,
    rootMargin: '0px 0px -150px 0px'
  })

  React.useEffect(() => {
    if (trackVisibility) {
      // Always scroll to bottom when trackVisibility is true (e.g., when sending a message)
      entry?.target.scrollIntoView({
        block: 'start',
        behavior: 'smooth'
      })
    } else if (isAtBottom) {
      // Only scroll to bottom if we're already near the bottom
      entry?.target.scrollIntoView({
        block: 'start'
      })
    }
  }, [inView, entry, isAtBottom, trackVisibility])

  return <div ref={ref} className="h-px w-full" />
}
