-- Migration: Add optional description column to webhook_endpoints table.
-- Phase 47-01: Outbound webhook CRUD backend.
--
-- Adds a free-text description so users can annotate their webhook endpoints
-- (e.g. "Zapier integration", "Custom CRM bridge").

ALTER TABLE webhook_endpoints
    ADD COLUMN IF NOT EXISTS description text;
