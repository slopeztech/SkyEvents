-- PostgreSQL initialisation script for SkyEvents development
-- This script runs once when the container is first created.

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- trigram search (for LIKE queries)
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- composite GIN indexes

-- Verify timezone
SET timezone = 'UTC';
