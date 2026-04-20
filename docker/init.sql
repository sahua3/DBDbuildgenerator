-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable pg_trgm for fuzzy text search on perk names
CREATE EXTENSION IF NOT EXISTS pg_trgm;
