'use client'

import { useState, useEffect } from 'react'
import { SidebarActions } from '@/components/sidebar-actions'
import { SidebarItem } from '@/components/sidebar-item'
import { getChats, removeChat, shareChat } from '@/app/actions'

export interface SidebarListProps {
  userId?: string
}

export function SidebarList({ userId }: SidebarListProps) {
  const [chats, setChats] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    const fetchChats = async () => {
      if (userId) {
        try {
          const chatData = await getChats(userId)
          setChats(chatData || [])
        } catch (error) {
          console.error('Error fetching chats:', error)
        } finally {
          setLoading(false)
        }
      } else {
        setChats([])
        setLoading(false)
      }
    }
    
    fetchChats()
  }, [userId])

  if (loading) {
    return (
      <div className="flex-1 overflow-auto p-8 text-center">
        <p className="text-sm text-muted-foreground">Loading chats...</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-auto">
      {chats?.length ? (
        <div className="space-y-2 px-2">
          {chats.map(
            chat =>
              chat && (
                <SidebarItem key={chat?.id} chat={chat}>
                  <SidebarActions
                    chat={chat}
                    removeChat={removeChat}
                    shareChat={shareChat}
                  />
                </SidebarItem>
              )
          )}
        </div>
      ) : (
        <div className="p-8 text-center">
          <p className="text-sm text-muted-foreground">No chat history</p>
        </div>
      )}
    </div>
  )
}
