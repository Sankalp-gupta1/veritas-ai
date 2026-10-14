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
