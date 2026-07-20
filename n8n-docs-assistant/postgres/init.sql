-- Runs once on the first start of the Postgres container.

-- pgvector extension for the knowledge base (used by n8n's PGVector node)
CREATE EXTENSION IF NOT EXISTS vector;

-- Separate database for n8n's own internal state (workflows, executions)
CREATE DATABASE n8n;

-- ---------------------------------------------------------------------------
-- Monitoring tables (module 5 concepts: log every conversation + feedback)
-- ---------------------------------------------------------------------------

-- One row per question answered by the assistant.
CREATE TABLE IF NOT EXISTS conversations (
    id                    TEXT PRIMARY KEY,
    question              TEXT NOT NULL,
    answer                TEXT NOT NULL,
    model                 TEXT,
    latency_ms            INTEGER,
    prompt_tokens         INTEGER,
    completion_tokens     INTEGER,
    total_tokens          INTEGER,
    cost_usd              NUMERIC(10, 6),
    relevance             TEXT,      -- filled asynchronously by the LLM judge
    relevance_explanation TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Thumbs up (+1) / thumbs down (-1) from the Streamlit UI.
CREATE TABLE IF NOT EXISTS feedback (
    id              SERIAL PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id),
    feedback        INTEGER NOT NULL CHECK (feedback IN (-1, 1)),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations (created_at);
CREATE INDEX IF NOT EXISTS idx_feedback_conversation_id ON feedback (conversation_id);
