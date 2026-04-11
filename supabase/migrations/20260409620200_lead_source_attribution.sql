-- Migration: 20260409620200_lead_source_attribution.sql
-- Description: Phase 62-02 — Lead source attribution and pipeline health columns.
--
-- SALES-02 / SALES-04: Extend source attribution on contacts with ad campaign
-- and email campaign enum values, UTM tracking fields, campaign_id foreign-key
-- column, and a last_activity_at helper column on hubspot_deals for staleness
-- detection.
--
-- All statements use IF NOT EXISTS / DO-block guards to remain idempotent.

-- -------------------------------------------------------------------------
-- 1. Extend contact_source enum with marketing attribution values
-- -------------------------------------------------------------------------

-- ADD VALUE IF NOT EXISTS is idempotent and safe in Postgres 9.1+.
ALTER TYPE public.contact_source ADD VALUE IF NOT EXISTS 'ad_campaign';
ALTER TYPE public.contact_source ADD VALUE IF NOT EXISTS 'email_campaign';

-- -------------------------------------------------------------------------
-- 2. Add UTM + campaign attribution columns to contacts
-- -------------------------------------------------------------------------

ALTER TABLE public.contacts
    ADD COLUMN IF NOT EXISTS campaign_id   UUID,
    ADD COLUMN IF NOT EXISTS utm_source    TEXT,
    ADD COLUMN IF NOT EXISTS utm_medium    TEXT,
    ADD COLUMN IF NOT EXISTS utm_campaign  TEXT;

-- -------------------------------------------------------------------------
-- 3. Indexes for attribution queries
-- -------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_contacts_campaign
    ON public.contacts (user_id, campaign_id)
    WHERE campaign_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_contacts_utm
    ON public.contacts (user_id, utm_source)
    WHERE utm_source IS NOT NULL;

-- -------------------------------------------------------------------------
-- 4. Add last_activity_at to hubspot_deals for staleness detection
-- -------------------------------------------------------------------------

ALTER TABLE public.hubspot_deals
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;
