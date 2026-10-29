import type { Kind } from "../types";

export const KIND_LABEL: Record<Kind, string> = { pdf: "PDF", markdown: "Markdown", text: "Text", url: "Web page", note: "Note" };

export function KindBadge({ kind }: { kind: Kind }) {
  return <span className={`kind kind-${kind}`}>{KIND_LABEL[kind]}</span>;
}

export function ago(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 30) return `${Math.floor(s / 86400)} d ago`;
  return new Date(iso).toLocaleDateString();
}
