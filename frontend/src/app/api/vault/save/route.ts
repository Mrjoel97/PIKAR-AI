// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * Save text content (e.g., a chat message) into the Knowledge Vault as a
 * note-style document. Uploads the content as a .txt file to the
 * `knowledge-vault` storage bucket and creates a matching vault_documents
 * row — so notes show up in the same Uploads tab as everything else and
 * are eligible for the standard embedding/search pipeline.
 *
 * POST body: { content: string, type?: 'note', session_id?: string, title?: string }
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const MAX_NOTE_BYTES = 256 * 1024; // 256 KiB safety cap

export async function POST(request: NextRequest) {
    const rl = rateLimiters.authenticated.check(getClientIp(request));
    if (!rl.success) {
        return NextResponse.json(
            { error: 'Too many requests' },
            { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } },
        );
    }

    try {
        const body = (await request.json().catch(() => ({}))) as {
            content?: unknown;
            type?: unknown;
            session_id?: unknown;
            title?: unknown;
        };

        const content = typeof body.content === 'string' ? body.content.trim() : '';
        if (!content) {
            return NextResponse.json({ error: 'content is required' }, { status: 400 });
        }
        if (content.length > MAX_NOTE_BYTES) {
            return NextResponse.json({ error: 'content too large' }, { status: 413 });
        }

        const noteType = typeof body.type === 'string' ? body.type : 'note';
        const sessionId = typeof body.session_id === 'string' ? body.session_id : null;
        const titleHint = typeof body.title === 'string' && body.title.trim()
            ? body.title.trim()
            : null;

        const supabase = await createClient();
        const { data: { user }, error: authError } = await supabase.auth.getUser();
        if (authError || !user) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }

        // First non-empty line (truncated) becomes a human-readable filename.
        const firstLine = content.split('\n').map((s) => s.trim()).find(Boolean) ?? 'note';
        const slug = (titleHint ?? firstLine)
            .replace(/[^a-zA-Z0-9 _-]+/g, '')
            .trim()
            .slice(0, 60) || 'note';
        const ts = Date.now();
        const filename = `${slug}.txt`;
        const filePath = `${user.id}/${ts}_${filename}`;

        const { error: uploadError } = await supabase.storage
            .from('knowledge-vault')
            .upload(filePath, content, {
                contentType: 'text/plain; charset=utf-8',
                upsert: false,
            });
        if (uploadError) {
            console.error('[api/vault/save] storage upload failed:', uploadError.message);
            return NextResponse.json(
                { error: 'storage upload failed', detail: uploadError.message },
                { status: 500 },
            );
        }

        const { data: row, error: dbError } = await supabase
            .from('vault_documents')
            .insert({
                user_id: user.id,
                filename,
                file_path: filePath,
                file_type: 'text/plain',
                size_bytes: new TextEncoder().encode(content).length,
                category: noteType === 'note' ? 'Chat Note' : noteType,
                is_processed: false,
                metadata: {
                    saved_from: 'chat',
                    session_id: sessionId,
                    note_type: noteType,
                },
            })
            .select('id, file_path')
            .single();

        if (dbError) {
            console.error('[api/vault/save] db insert failed:', dbError.message);
            // Best-effort cleanup so we don't orphan the storage object.
            await supabase.storage.from('knowledge-vault').remove([filePath]).catch(() => {});
            return NextResponse.json(
                { error: 'database insert failed', detail: dbError.message },
                { status: 500 },
            );
        }

        return NextResponse.json({ ok: true, id: row?.id ?? null, file_path: row?.file_path ?? filePath });
    } catch (err: unknown) {
        console.error('[api/vault/save] threw:', err);
        const message = err instanceof Error ? err.message : 'internal';
        return NextResponse.json({ error: message }, { status: 500 });
    }
}
