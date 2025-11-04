-- Purpose: Add AI analysis columns to jobs table (idempotent).
ALTER TABLE IF EXISTS jobs
    ADD COLUMN IF NOT EXISTS analysis_json JSONB,
    ADD COLUMN IF NOT EXISTS analysis_model VARCHAR(64),
    ADD COLUMN IF NOT EXISTS analysis_version INT,
    ADD COLUMN IF NOT EXISTS ai_started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ai_finished_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS ai_error TEXT;
