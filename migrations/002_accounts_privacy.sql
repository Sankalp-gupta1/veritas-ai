-- Additive: existing browser workspaces can be claimed during account creation.
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS cloud_enabled boolean NOT NULL DEFAULT false;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS save_history boolean NOT NULL DEFAULT false;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS privacy_version integer NOT NULL DEFAULT 1;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS encrypted boolean NOT NULL DEFAULT false;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS encrypted boolean NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS accounts (
  id uuid PRIMARY KEY,
  email_lookup text UNIQUE NOT NULL,
  email_encrypted text NOT NULL,
  password_hash text NOT NULL,
  recovery_hash text NOT NULL,
  workspace_id uuid UNIQUE NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash text PRIMARY KEY,
  account_id uuid NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_account ON sessions(account_id);
CREATE TABLE IF NOT EXISTS privacy_events (
  id uuid PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  event text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS privacy_events_workspace ON privacy_events(workspace_id,created_at DESC);
CREATE TABLE IF NOT EXISTS disclosure_consents (
  token_hash text PRIMARY KEY,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  payload_digest text NOT NULL,
  expires_at timestamptz NOT NULL,
  used boolean NOT NULL DEFAULT false
);
INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT DO NOTHING;
