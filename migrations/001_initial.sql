-- A fresh, dedicated database only. The app never runs migrations on startup.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS schema_migrations (
  version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY,
  token_hash text UNIQUE NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name text NOT NULL,
  sha256 text NOT NULL,
  page_count integer NOT NULL CHECK (page_count > 0),
  byte_count integer NOT NULL CHECK (byte_count > 0),
  pdf bytea NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(workspace_id, sha256)
);
CREATE INDEX IF NOT EXISTS documents_workspace ON documents(workspace_id);
CREATE TABLE IF NOT EXISTS pages (
  document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_number integer NOT NULL CHECK(page_number > 0),
  printed_label text,
  text text NOT NULL,
  PRIMARY KEY(document_id, page_number)
);
CREATE TABLE IF NOT EXISTS chunks (
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  page_number integer NOT NULL,
  start_offset integer NOT NULL,
  end_offset integer NOT NULL,
  text text NOT NULL,
  embedding vector(256) NOT NULL,
  embedding_model text NOT NULL,
  FOREIGN KEY(document_id, page_number) REFERENCES pages(document_id, page_number) ON DELETE CASCADE,
  CHECK(end_offset > start_offset)
);
CREATE INDEX IF NOT EXISTS chunks_document ON chunks(document_id);
-- Exact cosine search is intentional for the bounded 20-document workspace.
-- An ANN index requires measured recall/tenant filtering tests before adoption.
CREATE TABLE IF NOT EXISTS runs (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  question text NOT NULL,
  variant text NOT NULL,
  result jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_workspace ON runs(workspace_id, created_at DESC);
CREATE TABLE IF NOT EXISTS rate_limits (
  bucket text NOT NULL,
  window_id bigint NOT NULL,
  count integer NOT NULL,
  PRIMARY KEY(bucket, window_id)
);
INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING;

