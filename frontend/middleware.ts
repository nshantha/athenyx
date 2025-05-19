import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs'
import { NextResponse } from 'next/server'

import type { NextRequest } from 'next/server'

// Set this to true to enable authentication
const ENABLE_AUTH = true

export async function middleware(req: NextRequest) {
  const res = NextResponse.next()

  // Skip authentication if disabled
  if (!ENABLE_AUTH) {
    return res
  }

  // Check if Supabase URL is properly configured
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  
  // Skip authentication if Supabase is not configured
  if (!supabaseUrl || supabaseUrl === 'your-project-url' || 
      !supabaseAnonKey || supabaseAnonKey === 'your-anon-key') {
    return res
  }

  try {
    // Create a Supabase client configured to use cookies
    const supabase = createMiddlewareClient({ req, res })

    // Refresh session if expired - required for Server Components
    // https://supabase.com/docs/guides/auth/auth-helpers/nextjs#managing-session-with-middleware
    const {
      data: { session }
    } = await supabase.auth.getSession()

    // OPTIONAL: this forces users to be logged in to use the chatbot.
    // If you want to allow anonymous users, simply remove the check below.
    if (
      !session &&
      !req.url.includes('/sign-in') &&
      !req.url.includes('/sign-up')
    ) {
      const redirectUrl = req.nextUrl.clone()
      redirectUrl.pathname = '/sign-in'
      redirectUrl.searchParams.set(`redirectedFrom`, req.nextUrl.pathname)
      return NextResponse.redirect(redirectUrl)
    }
  } catch (error) {
    console.error('Middleware error:', error)
    // Return the response without authentication on error
    return res
  }

  return res
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - share (publicly shared chats)
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!share|api|_next/static|_next/image|favicon.ico).*)'
  ]
}
