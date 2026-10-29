import { describe, expect, it } from "vitest";
import type { Source } from "../types";
import { around, blocks, bySource, initial, inline, reduce } from "./answer";

describe("inline", () => {
  it("finds citations, bold and code", () => {
    expect(inline("Ends in **2020** [1][3, 4] via `pip`.")).toEqual([
      { type: "text", text: "Ends in " },
      { type: "bold", text: "2020" },
      { type: "text", text: " " },
      { type: "cite", n: 1 },
      { type: "cite", n: 3 },
      { type: "cite", n: 4 },
      { type: "text", text: " via " },
      { type: "code", text: "pip" },
      { type: "text", text: "." },
    ]);
  });

  it("leaves brackets that aren't citations alone", () => {
    expect(inline("a [x] b")).toEqual([{ type: "text", text: "a [x] b" }]);
  });
});

describe("blocks", () => {
  it("reads headings, lists and joined paragraphs", () => {
    const md = "Overview line one\nline two [1].\n\n### Releases\n- 3.0 in 2008 [2]\n* 2.7 last [3]\n1. numbered\n\nEnd.";
    const b = blocks(md);
    expect(b.map((x) => x.type)).toEqual(["para", "heading", "list", "para"]);
    expect(b[0]).toEqual({
      type: "para",
      inline: [{ type: "text", text: "Overview line one line two " }, { type: "cite", n: 1 }, { type: "text", text: "." }],
    });
    expect(b[2].type === "list" && b[2].items.length).toBe(3);
  });
});

const src = (n: number, doc: number): Source => ({
  n,
  chunk_id: n,
  document_id: doc,
  title: `Doc ${doc}`,
  kind: "note",
  heading: "",
  page: null,
  text: "t",
  score: 0.8,
  rerank: 1,
  cited: false,
});

it("groups sources by document in rank order", () => {
  const g = bySource([src(1, 7), src(2, 3), src(3, 7)]);
  expect(g.map((x) => [x.document_id, x.sources.map((s) => s.n)])).toEqual([
    [7, [1, 3]],
    [3, [2]],
  ]);
});

it("folds the event stream into state", () => {
  const events: [string, unknown][] = [
    ["sources", { sources: [src(1, 1), src(2, 2)], confidence: { level: "high", score: 0.8, threshold: 0.68 } }],
    ["token", { t: "2020 " }],
    ["token", { t: "【1】" }],
    ["answer", { answer: "2020 [1]", status: "answered", cited: [1] }],
    ["checking", { pairs: 1 }],
    ["conflicts", { items: [], pairs: 1 }],
    ["done", { id: 9, ms: 1200 }],
  ];
  const s = events.reduce((acc, [e, d]) => reduce(acc, e, d), initial);
  expect(s.draft).toBe("2020 【1】");
  expect(s.answer).toBe("2020 [1]");
  expect(s.sources.map((x) => x.cited)).toEqual([true, false]);
  expect([s.phase, s.queryId, s.pairs]).toEqual(["done", 9, 1]);
});

it("splits text around a passage", () => {
  expect(around("abcdef", 2, 4)).toEqual(["ab", "cd", "ef"]);
});
