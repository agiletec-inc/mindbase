-- Migration: multi-provider conversation embeddings.
--
-- MindBase originally stored one embedding per conversation in
-- conversations.embedding (a fixed vector(3072) for OpenAI text-embedding-3-large).
-- A pgvector column has a fixed dimension and vectors from different models are
-- not comparable, so that schema cannot hold embeddings from multiple providers
-- at the same time.
--
-- This table holds one row per (conversation, provider, model). Each row fills
-- exactly one dimension-bucket column so OpenAI (3072), bge-m3 (1024),
-- nomic-embed-text (768) and qwen3-embedding:8b (4096) can all coexist. Switching
-- the active provider is a config change (EMBEDDING_PROVIDER), and the same query
-- can be embedded by each provider and searched against its own vectors to
-- compare retrieval quality side by side.
--
-- No ANN (hnsw/ivfflat) index is created on purpose: pgvector 0.8 caps those at
-- 2000 dims for `vector` (4000 for `halfvec`), so 3072 and 4096 cannot be
-- indexed at all, and the conversation corpus is small enough that an exact
-- cosine scan is fast. Add a halfvec index later if the corpus grows past that.

CREATE TABLE IF NOT EXISTS conversation_embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    dim             INTEGER NOT NULL,
    vec_768         vector(768),
    vec_1024        vector(1024),
    vec_3072        vector(3072),
    vec_4096        vector(4096),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conversation_id, provider, model),
    -- Exactly one dimension-bucket column must be populated, and it must match dim.
    CONSTRAINT conversation_embeddings_one_vec CHECK (
        (vec_768 IS NOT NULL)::int
      + (vec_1024 IS NOT NULL)::int
      + (vec_3072 IS NOT NULL)::int
      + (vec_4096 IS NOT NULL)::int = 1
    ),
    CONSTRAINT conversation_embeddings_dim_match CHECK (
        (dim = 768  AND vec_768  IS NOT NULL) OR
        (dim = 1024 AND vec_1024 IS NOT NULL) OR
        (dim = 3072 AND vec_3072 IS NOT NULL) OR
        (dim = 4096 AND vec_4096 IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_conversation
    ON conversation_embeddings (conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_embeddings_provider_model
    ON conversation_embeddings (provider, model);
