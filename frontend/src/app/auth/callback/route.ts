import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get('code')
    const next = searchParams.get('next') ?? '/onboarding/welcome'

    if (code) {
        const supabase = await createClient()
        const { error } = await supabase.auth.exchangeCodeForSession(code)

        if (!error) {
            // Check if user needs onboarding or can go to dashboard
            const { data: { user } } = await supabase.auth.getUser()

            if (user) {
                const { data: profile } = await supabase
                    .from('user_profiles')
                    .select('onboarding_completed')
                    .eq('user_id', user.id)
                    .single()

                if (profile?.onboarding_completed) {
                    return NextResponse.redirect(`${origin}/dashboard`)
                }
            }

            return NextResponse.redirect(`${origin}${next}`)
        }
    }

    // Return to login with error if something fails
    return NextResponse.redirect(`${origin}/auth/login?error=auth_callback_error`)
}
