import { type Metadata } from 'next'
import { notFound, redirect } from 'next/navigation'

import { auth } from '@/auth'
import { getChat } from '@/app/actions'
import { Chat } from '@/components/chat'
import { cookies } from 'next/headers'

export const runtime = 'edge'
export const preferredRegion = 'home'

export interface ChatPageProps {
  params: {
    id: string
  }
}

export async function generateMetadata({
  params
}: ChatPageProps): Promise<Metadata> {
  const cookieStore = cookies()
  const session = await auth({ cookieStore })

  if (!session?.user) {
    return {}
  }

  const chat = await getChat(params.id)
  return {
    title: chat?.title.toString().slice(0, 50) ?? 'Chat'
  }
}

export default async function ChatPage({ params }: ChatPageProps) {
  console.log('ChatPage rendered with params:', params);
  
  const cookieStore = cookies()
  const session = await auth({ cookieStore })

  if (!session?.user) {
    console.log('No user session, redirecting to sign-in');
    redirect(`/sign-in?next=/chat/${params.id}`)
  }

  console.log('Fetching chat with ID:', params.id);
  const chat = await getChat(params.id)
  console.log('Chat fetch result:', chat ? 'Chat found' : 'Chat not found', chat?.id);

  if (!chat) {
    console.log('No chat found with ID:', params.id);
    notFound()
  }

  if (chat?.userId !== session?.user?.id) {
    console.log('Chat user ID mismatch', { chatUserId: chat?.userId, sessionUserId: session?.user?.id });
    notFound()
  }

  console.log('Rendering chat component with ID:', chat.id, 'and message count:', chat.messages?.length || 0);
  return <Chat id={chat.id} initialMessages={chat.messages} />
}
