export type DocumentRecord = {
  id: string;
  name: string;
  page_count: number;
  byte_count: number;
  sha256: string;
  created_at: string;
};
export type Citation = {
  chunk_id: string;
  document_id?: string;
  document_name?: string;
  document_sha256?: string;
  page_number?: number;
  printed_label?: string;
  quote: string;
  integrity: boolean;
  relation: string;
  start_offset?: number;
  end_offset?: number;
  support_score?: number;
};
export type Claim = {
  id: string;
  text: string;
  verdict:
    "supported" | "conflict" | "contradicted" | "insufficient" | "not_checked";
  explanation: string;
  citations: Citation[];
  counter_evidence: Citation[];
};
export type Answer = {
  privacy?: { history_saved: boolean; external_ai: boolean; storage: string; processing: string };
  id: string;
  question: string;
  variant: string;
  answer: string;
  answer_kind: string;
  abstained: boolean;
  claims: Claim[];
  counts: Record<string, number>;
  generation: {
    provider: string;
    model: string;
    usage: Record<string, number>;
  };
  timings: Record<string, number>;
  latency_ms: number;
  notes: string[];
  audit: Record<string, unknown>;
};
export type Run = {
  id: string;
  question: string;
  variant: string;
  created_at: string;
  counts: Record<string, number>;
  latency_ms: number;
  abstained: boolean;
};
export type Settings = {
  provider: "extractive" | "gemini" | "ollama";
  model: string;
  key: string;
};

export type Account = {
  id: string;
  email: string;
  email_verified: boolean;
  workspace_id: string;
  cloud_enabled: boolean;
  save_history: boolean;
  idle_timeout_minutes: number;
};
export type Disclosure = {
  consent_token: string;
  recipient: string;
  expires_in_seconds: number;
  notice: string;
  masked: Record<string, number>;
  payloads: { method: string; question: string; evidence: { chunk_id: string; source: string; text: string }[] }[];
};
