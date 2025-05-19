import { createChat } from '@/app/actions'
import { Chat } from '@/components/chat'
import { redirect } from 'next/navigation'

export const runtime = 'edge'

export default async function IndexPage() {
  // Create a new chat in the database and redirect to it
  const result = await createChat()
  
  if ('error' in result) {
    // If there was an error, render an empty chat
    // This will still work but might not save to DB
    return <Chat />
  }
  
  // Redirect to the new chat page
  redirect(`/chat/${result.id}`)
}
