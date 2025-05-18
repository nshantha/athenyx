'use client'

import { useState } from 'react'
import { type Message } from '@/lib/types'

import { Button } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { IconCheck, IconCopy } from '@/components/ui/icons'

interface ChatMessageActionsProps extends React.ComponentProps<'div'> {
  message: Message
}

export function ChatMessageActions({
  message,
  className,
  ...props
}: ChatMessageActionsProps) {
  const [isCopied, setIsCopied] = useState<boolean>(false)

  const onCopy = () => {
    if (isCopied) return
    if (!navigator.clipboard) return

    navigator.clipboard.writeText(message.content)
    setIsCopied(true)

    setTimeout(() => {
      setIsCopied(false)
    }, 2000)
  }

  return (
    <div
      className="flex items-center justify-end transition-opacity group-hover:opacity-100 md:absolute md:-right-10 md:-top-2 md:opacity-0"
      {...props}
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={onCopy}
          >
            {isCopied ? <IconCheck /> : <IconCopy />}
            <span className="sr-only">Copy message</span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>Copy message</TooltipContent>
      </Tooltip>
    </div>
  )
}
