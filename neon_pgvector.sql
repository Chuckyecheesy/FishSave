-- pgvector extension and embeddings table for RAG / similarity search.
-- Run this against your Neon database (after neon_schema.sql).
-- Cohere embed-multilingual-v3.0 / embed-english-v3.0 use 1024 dimensions.

CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- Table: context_embeddings
-- Stores text chunks and their vector embeddings for semantic search (RAG).
-- Source rows (e.g. country_risk_category, forecast_metrics) can be joined via
-- source_type + source_id.
-- =============================================================================
CREATE TABLE IF NOT EXISTS context_embeddings (
  id           SERIAL PRIMARY KEY,
  source_type  TEXT NOT NULL,
  source_id    TEXT NOT NULL,
  content      TEXT NOT NULL,
  embedding    vector(1024) NOT NULL,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(source_type, source_id)
);

COMMENT ON TABLE context_embeddings IS 'Vector embeddings of context_meaning and other text for RAG. Use cosine distance or inner product for similarity search.';
COMMENT ON COLUMN context_embeddings.source_type IS 'Table or entity name, e.g. country_risk_category, forecast_metrics, risk_score_intervals.';
COMMENT ON COLUMN context_embeddings.source_id IS 'Unique id within source_type, e.g. country name or (country,year,horizon).';
COMMENT ON COLUMN context_embeddings.content IS 'Original text that was embedded.';
COMMENT ON COLUMN context_embeddings.embedding IS '1024-dim vector from Cohere embed-multilingual-v3.0 (or embed-english-v3.0).';

-- HNSW index for fast approximate nearest-neighbor search (cosine distance).
-- Use: ORDER BY embedding <=> query_embedding LIMIT k
CREATE INDEX IF NOT EXISTS context_embeddings_embedding_hnsw
  ON context_embeddings
  USING hnsw (embedding vector_cosine_ops);
