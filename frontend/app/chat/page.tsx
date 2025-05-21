import { getChats } from '@/app/actions'
import { auth } from '@/auth'
import { Chat } from '@/components/chat'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export const runtime = 'edge'

export default async function ChatPage() {
  // Get the current user session
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
  
  if (!session?.user) {
    redirect('/sign-in')
  }
  
  // Check if the user already has any chats
  const existingChats = await getChats(session.user.id)
  
  if (existingChats.length > 0) {
    // If user has existing chats, redirect to the most recent one
    redirect(`/chat/${existingChats[0].id}`)
    return null
  }
  
  // Instead of creating a new chat automatically, show an empty chat interface
  // The chat will only be created when the user sends a message
  return <Chat initialMessages={[]} id="new" />
} 