import React from 'react'
import { Button } from '@/components/ui/button'
import { IconArrowRight } from '@/components/ui/icons'
import { useRepository } from '@/lib/repository-context'

const exampleMessages = [
  {
    heading: 'Explain code structure',
    message: `What is the main structure of this codebase?`
  },
  {
    heading: 'Find implementation details',
    message: 'How is authentication implemented in this project?'
  },
  {
    heading: 'Explain functionality',
    message: `Explain how the repository indexing works`
  }
]

interface EmptyScreenProps {
  setInput: (input: string) => void
}

export function EmptyScreen({ setInput }: EmptyScreenProps) {
  const { activeRepository } = useRepository()

  return (
    <div className="w-full px-0 flex flex-col items-center">
      <div className="rounded-lg border bg-background p-8 w-full max-w-3xl">
        <h1 className="mb-2 text-lg font-semibold">
          Welcome to Actuamind Code Explorer!
        </h1>
        <p className="mb-2 leading-normal text-muted-foreground">
          This is an AI-powered code exploration tool.
        </p>
        
        {!activeRepository ? (
          <div className="mt-4 bg-blue-950/20 p-4 rounded-md border border-blue-800/30">
            <h2 className="text-base font-medium text-blue-400 mb-2">Getting Started</h2>
            <p className="text-sm text-muted-foreground mb-3">
              To begin exploring code, please select or add a repository from the sidebar.
            </p>
            <div className="flex items-center space-x-2 text-sm">
              <span className="bg-blue-900/50 rounded-full w-6 h-6 flex items-center justify-center">1</span>
              <span>Use the repository panel in the sidebar to manage repositories</span>
            </div>
            <div className="flex items-center space-x-2 text-sm mt-2">
              <span className="bg-blue-900/50 rounded-full w-6 h-6 flex items-center justify-center">2</span>
              <span>Add a new Git repository to be indexed and analyzed</span>
            </div>
            <div className="flex items-center space-x-2 text-sm mt-2">
              <span className="bg-blue-900/50 rounded-full w-6 h-6 flex items-center justify-center">3</span>
              <span>Select a repository to set it as active for queries</span>
            </div>
          </div>
        ) : (
          <>
            <p className="leading-normal text-muted-foreground">
              You can start a conversation here or try the following examples:
            </p>
            <div className="mt-4 flex flex-col items-start space-y-2">
              {exampleMessages.map((message, index) => (
                <Button
                  key={index}
                  variant="link"
                  className="h-auto p-0 text-base"
                  onClick={() => setInput(message.message)}
                >
                  <IconArrowRight className="mr-2 text-muted-foreground" />
                  {message.heading}
                </Button>
              ))}
            </div>
            
            <div className="mt-6 bg-green-950/20 p-4 rounded-md border border-green-800/30">
              <h2 className="text-base font-medium text-green-400 mb-2">
                Currently exploring: {activeRepository.service_name}
              </h2>
              <p className="text-sm text-muted-foreground break-all">
                {activeRepository.url}
              </p>
              {activeRepository.description && (
                <p className="text-sm mt-2">{activeRepository.description}</p>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}