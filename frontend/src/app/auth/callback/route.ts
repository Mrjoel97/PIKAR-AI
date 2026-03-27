// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get('code')

    const codeError = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    if (codeError) {
        console.error('Auth callback error:', codeError, errorDescription)
        return NextResponse.redirect(
            `${origin}/auth/login?error=${encodeURIComponent(codeError)}&error_description=${encodeURIComponent(errorDescription || '')}`
        )
    }

    if (code) {
        const supabase = await createClient()
        const { error } = await supabase.auth.exchangeCodeForSession(code)

        if (!error) {
            // Redirect to dashboard — middleware handles onboarding/persona routing.
            // This avoids a redundant DB query in the callback, making login ~200ms faster.
            return NextResponse.redirect(`${origin}/dashboard/command-center`)
        } else {
            console.error('Exchange code error:', error)
            return NextResponse.redirect(
                `${origin}/auth/login?error=exchange_code_error&error_description=${encodeURIComponent(error.message)}`
            )
        }
    }

    return NextResponse.redirect(`${origin}/auth/login?error=no_code`)
}
