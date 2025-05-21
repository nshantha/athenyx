import { Chat } from '@/components/chat'
import { auth } from '@/auth'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

export const runtime = 'edge'

export default async function IndexPage() {
  // Get the current user session
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
  
  if (!session?.user) {
    redirect('/sign-in')
  }
  
  // Instead of redirecting to /chat and automatically creating a new chat,
  // we display the chat interface with the empty UI state and a temporary ID
  // The ID 'new' will be replaced when the user sends their first message
  return <Chat initialMessages={[]} id="new" />
}
