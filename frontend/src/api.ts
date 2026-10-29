import { postStream } from "./lib/sse";
import type { Collection, Doc, DocFull, Mode, QueryFull, QuerySummary, Stats } from "./types";

// Empty in dev (Vite proxies /api). Set VITE_API_URL when the API is elsewhere.
export const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, credentials: "include" });
  } catch {
    throw new ApiError(0, "Can't reach the Papertrail server");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // FastAPI validation errors come as a list
    const msg =
      typeof body.detail === "string" ? body.detail : Array.isArray(body.detail) ? body.detail[0]?.msg : res.statusText;
    throw new ApiError(res.status, msg || `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export interface AskBody {
  query: string;
  mode: Mode;
  document_ids: number[] | null;
  collection: string | null;
  check_conflicts: boolean;
}

export const pageUrl = (docId: number, page: number, chunk?: number) =>
  `${BASE}/api/documents/${docId}/pages/${page}.png${chunk !== undefined ? `?chunk=${chunk}` : ""}`;

export const api = {
  me: () => request<{ owner: boolean }>("/api/auth/me"),
  login: (password: string) => request("/api/auth/login", json("POST", { password })),
  logout: () => request("/api/auth/logout", json("POST")),

  documents: (params: { collection?: string; q?: string } = {}) => {
    const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v) as [string, string][]);
    return request<Doc[]>(`/api/documents${qs.size ? `?${qs}` : ""}`);
  },
  collections: () => request<Collection[]>("/api/collections"),
  stats: () => request<Stats>("/api/stats"),
  document: (id: number) => request<DocFull>(`/api/documents/${id}`),
  upload: (files: File[], collection: string) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    form.append("collection", collection);
    return request<Doc[]>("/api/documents/upload", { method: "POST", body: form });
  },
  addUrl: (url: string, collection: string) => request<Doc>("/api/documents/url", json("POST", { url, collection })),
  addNote: (title: string, content: string, collection: string) =>
    request<Doc>("/api/documents/note", json("POST", { title, content, collection })),
  update: (id: number, patch: { title?: string; collection?: string; content?: string }) =>
    request<Doc>(`/api/documents/${id}`, json("PATCH", patch)),
  reindex: (id: number) => request<Doc>(`/api/documents/${id}/reindex`, json("POST")),
  remove: (id: number) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),

  ask: (body: AskBody, onEvent: (event: string, data: unknown) => void, signal?: AbortSignal) =>
    postStream(`${BASE}/api/ask`, body, onEvent, signal),
  queries: () => request<QuerySummary[]>("/api/queries"),
  query: (id: number) => request<QueryFull>(`/api/queries/${id}`),
  removeQuery: (id: number) => request<void>(`/api/queries/${id}`, { method: "DELETE" }),
};
