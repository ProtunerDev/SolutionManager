-- Migration: add created_by to solutions
-- Run once against existing databases (dev and production)
ALTER TABLE solutions ADD COLUMN IF NOT EXISTS created_by TEXT;
