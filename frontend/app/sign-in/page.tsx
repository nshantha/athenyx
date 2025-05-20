import { auth } from '@/auth'
import { LoginButton } from '@/components/login-button'
import { LoginForm } from '@/components/login-form'
import { Separator } from '@/components/ui/separator'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { getChats } from '@/app/actions'

export default async function SignInPage() {
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
  
  // redirect to appropriate page if user is already logged in
  if (session?.user) {
    // Check if the user has any existing chats
    const existingChats = await getChats(session.user.id)
    
    if (existingChats.length > 0) {
      // If they have chats, redirect to their most recent chat
      redirect(`/chat/${existingChats[0].id}`)
    } else {
      // If no chats, redirect to /chat which will create a new one
      redirect('/chat')
    }
  }
  
  return (
    <div className="flex h-[calc(100vh-theme(spacing.16))] flex-col items-center justify-center py-10">
      <div className="w-full max-w-sm">
        <LoginForm action="sign-in" />
        <Separator className="my-4" />
        <div className="flex justify-center">
          <LoginButton />
        </div>
      </div>
    </div>
  )
}
