// The model answers in a small slice of Markdown (### headings, bullets, **bold**,
// `code`) with [n] citations. This turns it into blocks and inline pieces the page can
// render, citation numbers included, without an HTML-producing Markdown library.

import type { AnswerStatus, Confidence, Conflict, Source } from "../types";

export type Inline =
  | { type: "text"; text: string }
  | { type: "bold"; text: string }
  | { type: "code"; text: string }
  | { type: "cite"; n: number };

export type Block =
  | { type: "heading"; inline: Inline[] }
  | { type: "list"; items: Inline[][] }
  | { type: "para"; inline: Inline[] };

const TOKEN = /\[(\d+(?:\s*,\s*\d+)*)\]|\*\*([^*]+)\*\*|`([^`]+)`/g;

export function inline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(TOKEN)) {
    if (m.index > last) out.push({ type: "text", text: text.slice(last, m.index) });
    if (m[1]) for (const n of m[1].split(",")) out.push({ type: "cite", n: Number(n.trim()) });
    else if (m[2]) out.push({ type: "bold", text: m[2] });
    else out.push({ type: "code", text: m[3] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ type: "text", text: text.slice(last) });
  return out;
}

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;

export function blocks(md: string): Block[] {
  const out: Block[] = [];
  let para: string[] = [];
  const flush = () => {
    if (para.length) out.push({ type: "para", inline: inline(para.join(" ")) });
    para = [];
  };
  for (const raw of md.split("\n")) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }
    const heading = line.match(/^#{1,6}\s+(.*)$/);
    if (heading) {
      flush();
      out.push({ type: "heading", inline: inline(heading[1]) });
    } else if (BULLET.test(line)) {
      flush();
      const item = inline(line.replace(BULLET, ""));
      const prev = out[out.length - 1];
      if (prev?.type === "list") prev.items.push(item);
      else out.push({ type: "list", items: [item] });
    } else {
      para.push(line);
    }
  }
  flush();
  return out;
}

export interface SourceGroup {
  document_id: number;
  title: string;
  kind: Source["kind"];
  sources: Source[];
}

/** Sources grouped by document, documents in the order their first passage ranked. */
export function bySource(sources: Source[]): SourceGroup[] {
  const groups = new Map<number, SourceGroup>();
  for (const s of sources) {
    const g = groups.get(s.document_id) ?? { document_id: s.document_id, title: s.title, kind: s.kind, sources: [] };
    g.sources.push(s);
    groups.set(s.document_id, g);
  }
  return [...groups.values()];
}

// --- the stream ---------------------------------------------------------------------

export interface AskState {
  phase: "idle" | "retrieving" | "writing" | "checking" | "done";
  sources: Source[];
  confidence: Confidence | null;
  draft: string; // what has streamed so far
  answer: string; // final, citations normalised
  status: AnswerStatus | null;
  cited: number[];
  conflicts: Conflict[];
  pairs: number | null; // passage pairs checked for conflicts; null = check didn't run
  notices: string[];
  queryId: number | null;
  ms: number | null;
}

export const initial: AskState = {
  phase: "idle",
  sources: [],
  confidence: null,
  draft: "",
  answer: "",
  status: null,
  cited: [],
  conflicts: [],
  pairs: null,
  notices: [],
  queryId: null,
  ms: null,
};

export function reduce(s: AskState, event: string, data: any): AskState {
  switch (event) {
    case "sources":
      return { ...s, phase: "writing", sources: data.sources, confidence: data.confidence };
    case "token":
      return { ...s, draft: s.draft + data.t };
    case "answer": {
      const cited = new Set<number>(data.cited);
      return {
        ...s,
        answer: data.answer,
        status: data.status,
        cited: data.cited,
        sources: s.sources.map((x) => ({ ...x, cited: cited.has(x.n) })),
      };
    }
    case "checking":
      return { ...s, phase: "checking" };
    case "conflicts":
      return { ...s, conflicts: data.items, pairs: data.pairs };
    case "notice":
      return { ...s, notices: [...s.notices, data.message] };
    case "done":
      return { ...s, phase: "done", queryId: data.id, ms: data.ms };
    default:
      return s;
  }
}

/** Splits text around [start, end) so the passage can be marked inside its document. */
export function around(text: string, start: number, end: number): [string, string, string] {
  return [text.slice(0, start), text.slice(start, end), text.slice(end)];
}
