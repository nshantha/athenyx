import React from 'react'
import { Button } from '@/components/ui/button'
import { PromptForm } from '@/components/prompt-form'
import { ButtonScrollToBottom } from '@/components/button-scroll-to-bottom'
import { IconRefresh, IconStop } from '@/components/ui/icons'
import { Message } from '@/lib/types'
import { useSidebar } from '@/lib/sidebar-context'
import { cn } from '@/lib/utils'

export interface ChatPanelProps {
  id?: string
  isLoading: boolean
  stop: () => void
  append: (message: { content: string }) => void
  reload: () => void
  input: string
  setInput: (input: string) => void
  messages: Message[]
  onSubmit?: (e: React.FormEvent<HTMLFormElement>) => void
  sidebarAdjustment?: string
}

export function ChatPanel({
  id,
  isLoading,
  stop,
  append,
  reload,
  input,
  setInput,
  messages,
  onSubmit,
  sidebarAdjustment = ''
}: ChatPanelProps) {
  const { isExpanded } = useSidebar()
  
  // Apply sidebar adjustment directly as a style
  const sidebarOffsetStyle = isExpanded 
    ? { marginLeft: 'var(--sidebar-width, 0px)' } 
    : {}
  
  return (
    <div className="fixed inset-x-0 bottom-0 bg-gradient-to-b from-muted/10 from-10% to-muted/30 to-50%">
      <ButtonScrollToBottom />
      <div 
        className="relative mx-auto w-full flex justify-center transition-all duration-300 ease-in-out"
        style={sidebarOffsetStyle}
      >
        <div className="w-full max-w-3xl px-4">
          <div className="flex h-10 items-center justify-center">
            {isLoading ? (
              <Button
                variant="outline"
                onClick={() => stop()}
                className="bg-background"
              >
                <IconStop className="mr-2" />
                Stop generating
              </Button>
            ) : (
              messages?.length > 0 && (
                <Button
                  variant="outline"
                  onClick={() => reload()}
                  className="bg-background"
                >
                  <IconRefresh className="mr-2" />
                  Regenerate response
                </Button>
              )
            )}
          </div>
          <div className="space-y-4 border-t bg-background py-2 shadow-lg sm:rounded-t-xl sm:border md:py-4">
            <PromptForm
              onSubmit={async (value) => {
                if (onSubmit) {
                  // If onSubmit is provided, use the form's submit handler
                  return
                }
                // Otherwise use the append function
                append({
                  content: value
                })
              }}
              input={input}
              setInput={setInput}
              isLoading={isLoading}
              formProps={onSubmit ? { onSubmit } : undefined}
              isEmptyScreen={false}
            />
          </div>
        </div>
      </div>
    </div>
  )
}