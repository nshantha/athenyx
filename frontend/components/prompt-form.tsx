import * as React from 'react'
import Link from 'next/link'
import Textarea from 'react-textarea-autosize'

import { useEnterSubmit } from '@/lib/hooks/use-enter-submit'
import { cn } from '@/lib/utils'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { IconArrowElbow, IconPlus } from '@/components/ui/icons'

export interface PromptProps {
  onSubmit: (value: string) => Promise<void>
  input: string
  setInput: (value: string) => void
  isLoading: boolean
  formProps?: React.FormHTMLAttributes<HTMLFormElement>
  isEmptyScreen?: boolean
}

export function PromptForm({
  onSubmit,
  input,
  setInput,
  isLoading,
  formProps,
  isEmptyScreen = false
}: PromptProps) {
  const { formRef, onKeyDown } = useEnterSubmit()
  const inputRef = React.useRef<HTMLTextAreaElement>(null)

  React.useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!input?.trim()) {
      return
    }
    setInput('')
    await onSubmit(input)
  }

  return (
    <form
      onSubmit={formProps?.onSubmit || handleSubmit}
      ref={formRef}
      {...formProps}
      className="w-full mx-auto max-w-3xl px-4"
    >
      <div 
        className={cn(
          "relative flex max-h-60 w-full grow flex-col overflow-hidden bg-background rounded-md border sm:px-4",
          isEmptyScreen && "shadow-lg"
        )}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <Link
              href="/"
              className={cn(
                buttonVariants({ size: 'sm', variant: 'outline' }),
                'absolute left-2 top-4 h-8 w-8 rounded-full bg-background p-0 sm:left-4'
              )}
            >
              <IconPlus />
              <span className="sr-only">New Chat</span>
            </Link>
          </TooltipTrigger>
          <TooltipContent>New Chat</TooltipContent>
        </Tooltip>
        <Textarea
          ref={inputRef}
          tabIndex={0}
          onKeyDown={onKeyDown}
          rows={1}
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={isEmptyScreen ? "Ask me anything..." : "Ask your knowledge base..."}
          spellCheck={false}
          className="min-h-[60px] w-full resize-none bg-transparent px-12 py-[1.3rem] focus-within:outline-none sm:text-sm"
        />
        <div className="absolute right-2 top-4 sm:right-4">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="submit"
                size="icon"
                disabled={isLoading || input === ''}
              >
                <IconArrowElbow />
                <span className="sr-only">Send message</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Send message</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </form>
  )
}