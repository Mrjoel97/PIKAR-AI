-- Inbound emails received via Resend webhook
-- Stores all email metadata + body for programmatic processing and forwarding

create table if not exists public.inbound_emails (
    id              uuid primary key default gen_random_uuid(),
    resend_email_id text unique not null,           -- Resend's email ID from webhook
    from_address    text not null,
    to_addresses    text[] not null default '{}',
    cc_addresses    text[] not null default '{}',
    bcc_addresses   text[] not null default '{}',
    subject         text,
    body_html       text,                           -- fetched via Resend Received Emails API
    body_text       text,                           -- plain-text version
    headers         jsonb not null default '{}',
    attachments     jsonb not null default '[]',     -- metadata array from webhook
    message_id      text,                           -- RFC 822 Message-ID header
    status          text not null default 'received' check (status in (
                        'received', 'forwarded', 'processed', 'failed'
                    )),
    forwarded_to    text,                           -- email address it was forwarded to
    forwarded_at    timestamptz,
    processed_at    timestamptz,
    error_message   text,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- Index for querying by status (processing queue)
create index if not exists idx_inbound_emails_status on public.inbound_emails (status);

-- Index for looking up by sender
create index if not exists idx_inbound_emails_from on public.inbound_emails (from_address);

-- Index for chronological listing
create index if not exists idx_inbound_emails_created on public.inbound_emails (created_at desc);

-- Auto-update updated_at
create or replace function public.update_inbound_emails_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_inbound_emails_updated_at
    before update on public.inbound_emails
    for each row
    execute function public.update_inbound_emails_updated_at();

-- RLS: service role only (webhook writes, no user access needed)
alter table public.inbound_emails enable row level security;

-- Allow service role full access
create policy "Service role full access on inbound_emails"
    on public.inbound_emails
    for all
    using (true)
    with check (true);
