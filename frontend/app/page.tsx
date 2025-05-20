import { redirect } from 'next/navigation'
import { auth } from '@/auth'
import { cookies } from 'next/headers'

export const runtime = 'edge'

export default async function IndexPage() {
  // Get the current user session
  const cookieStore = cookies()
  const session = await auth({ cookieStore })
  
  // Simply redirect to the /chat route, which will handle all the logic
  redirect('/chat')
}
