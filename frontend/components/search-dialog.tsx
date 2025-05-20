'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'react-hot-toast'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { IconMessage, IconSearch, IconSpinner } from '@/components/ui/icons'
import { searchChats } from '@/app/actions'
import { type Chat } from '@/lib/types'
import { cn } from '@/lib/utils'

interface SearchDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SearchDialog({ open, onOpenChange }: SearchDialogProps) {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = React.useState('')
  const [isSearching, setIsSearching] = React.useState(false)
  const [searchResults, setSearchResults] = React.useState<Chat[]>([])
  const inputRef = React.useRef<HTMLInputElement>(null)
  
  // Focus input when dialog opens
  React.useEffect(() => {
    if (open) {
      setTimeout(() => {
        inputRef.current?.focus()
      }, 0)
    } else {
      // Clear search state when dialog closes
      setSearchQuery('')
      setSearchResults([])
    }
  }, [open])
  
  // Handle search
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!searchQuery.trim()) {
      return
    }
    
    setIsSearching(true)
    
    try {
      const results = await searchChats(searchQuery)
      setSearchResults(results)
      
      if (results.length === 0) {
        toast.error('No chats found matching your search')
      }
    } catch (error) {
      console.error('Error searching chats:', error)
      toast.error('Failed to search chats')
    } finally {
      setIsSearching(false)
    }
  }
  
  // Navigate to a chat and close dialog
  const navigateToChat = (chatId: string) => {
    router.push(`/chat/${chatId}`)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Search Chats</DialogTitle>
          <DialogDescription>
            Search through your conversation titles and content
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSearch} className="flex w-full gap-2">
          <Input
            ref={inputRef}
            placeholder="Search your chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1"
          />
          <Button 
            type="submit" 
            disabled={!searchQuery.trim() || isSearching}
          >
            {isSearching ? (
              <IconSpinner className="mr-2 animate-spin" />
            ) : (
              <IconSearch className="mr-2" />
            )}
            Search
          </Button>
        </form>
        
        {searchResults.length > 0 && (
          <div className="mt-4 space-y-2 max-h-[300px] overflow-y-auto pr-2">
            <h3 className="text-sm font-medium">Results:</h3>
            {searchResults.map((chat) => (
              <div 
                key={chat.id}
                className="flex items-center border p-3 rounded hover:bg-muted cursor-pointer transition-colors"
                onClick={() => navigateToChat(chat.id)}
              >
                <div className="mr-2">
                  <IconMessage className="text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{chat.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(chat.createdAt).toLocaleDateString()} • {chat.messages.length} messages
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
        
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
} 