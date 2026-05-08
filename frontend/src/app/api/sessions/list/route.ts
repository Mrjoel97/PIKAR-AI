// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Server-side proxy for GET /sessions on the Pikar backend.
 *
 * The page used to call the backend directly from the browser using a
 * client-resolved access token. On hard reload there is a brief window
 * where the cookie token is unavailable and the call fails; the silent
 * catch in SessionControlContext then painted an empty Chat History
 * page. This route uses the SSR Supabase client to read the cookie JWT
 * authoritatively, so the auth race is gone.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
    const { searchParams } = new URL(request.url)
    const limitParam = searchParams.get('limit') ?? '50'
    const limit = Math.min(Math.max(parseInt(limitParam, 10) || 50, 1), 100)

    try {
        const supabase = await createClient()
        const [{ data: userData }, { data: sessionData }] = await Promise.all([
            supabase.auth.getUser(),
            supabase.auth.getSession(),
        ])
        if (!userData.user) {
            return NextResponse.json({ error: 'unauthenticated' }, { status: 401 })
        }
        const accessToken = sessionData.session?.access_token
        if (!accessToken) {
            return NextResponse.json({ error: 'no access token' }, { status: 401 })
        }

        const url = `${BACKEND_URL}/sessions?limit=${limit}`
        const upstream = await fetch(url, {
            headers: { Authorization: `Bearer ${accessToken}` },
            cache: 'no-store',
        })

        if (!upstream.ok) {
            const isUpstreamFailure = upstream.status >= 500
            console.error('[api/sessions/list] backend returned', upstream.status)
            return NextResponse.json(
                { error: 'upstream_error', upstream_status: upstream.status },
                { status: isUpstreamFailure ? 502 : upstream.status },
            )
        }

        const body = await upstream.json()
        return NextResponse.json(body)
    } catch (err) {
        console.error('[api/sessions/list] threw:', err)
        return NextResponse.json({ error: 'internal' }, { status: 500 })
    }
}
