import { createChat, getChats } from '@/app/actions'
import { auth } from '@/auth'
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
  
  // Only create a new chat if the user has no existing chats
  const result = await createChat()
  
  if ('error' in result) {
    console.error('Error creating chat:', result.error)
  }
  
  // Redirect to the new chat or home if there was an error
  if ('error' in result) {
    redirect('/')
  } else {
    redirect(`/chat/${result.id}`)
  }
  
  return null
} 