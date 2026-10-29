export type Kind = "pdf" | "markdown" | "text" | "url" | "note";
export type Status = "processing" | "ready" | "failed";

export interface Doc {
  id: number;
  kind: Kind;
  title: string;
  filename: string;
  source_url: string;
  collection: string;
  pages: number | null;
  chars: number;
  status: Status;
  error: string;
  chunks: number;
  created_at: string;
  updated_at: string;
}

export interface Passage {
  id: number;
  idx: number;
  heading: string;
  start: number | null;
  end: number | null;
  page: number | null;
  text: string;
}

export interface DocFull extends Doc {
  content: string;
  passages: Passage[];
}

export interface Collection {
  name: string;
  documents: number;
}

export interface Stats {
  documents: number;
  by_kind: Partial<Record<Kind, number>>;
  passages: number;
  processing: number;
  failed: number;
}

export interface Source {
  n: number;
  chunk_id: number;
  document_id: number;
  title: string;
  kind: Kind;
  heading: string;
  page: number | null;
  text: string;
  score: number;
  rerank: number;
  cited: boolean;
}

export interface Confidence {
  level: "high" | "medium" | "low";
  score: number;
  threshold: number;
}

export interface Conflict {
  topic: string;
  claim_a: string;
  claim_b: string;
  note: string;
  a: number;
  b: number;
  similarity: number;
}

export type Mode = "ask" | "topic";
export type AnswerStatus = "answered" | "not_found" | "declined" | "error" | "stopped";

export interface Scope {
  document_ids: number[] | null;
  collection: string | null;
}

export interface QuerySummary {
  id: number;
  mode: Mode;
  text: string;
  status: AnswerStatus;
  created_at: string;
  conflict_count: number;
}

export interface QueryFull extends QuerySummary {
  answer: string;
  scope: Scope;
  sources: Source[];
  conflicts: Conflict[];
  confidence: Confidence | Record<string, never>;
  model: string;
  ms: number;
}
