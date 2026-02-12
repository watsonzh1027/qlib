-- Migration: add created_at to funding_rates
-- Adds a created_at timestamp with timezone defaulting to NOW()
-- Safe to run multiple times (uses IF NOT EXISTS)

BEGIN;

ALTER TABLE IF EXISTS funding_rates
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Optionally backfill existing rows' created_at from updated_at if desired
-- Uncomment the following if you want to set created_at for existing rows:
-- UPDATE funding_rates SET created_at = COALESCE(created_at, updated_at);

COMMIT;
