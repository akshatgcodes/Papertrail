import { useEffect, useReducer, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import Result from "../components/Result";
import TopBar from "../components/TopBar";
import { initial, reduce, type AskState } from "../lib/answer";
import type { Collection, Doc, Mode } from "../types";

type Action = { type: "reset" } | { type: "start" } | { type: "event"; event: string; data: unknown } | { type: "fail"; message: string };

function reducer(s: AskState, a: Action): AskState {
  if (a.type === "reset") return initial;
  if (a.type === "start") return { ...initial, phase: "retrieving" };
  if (a.type === "fail") return { ...s, phase: "done", status: s.status ?? "error", notices: [...s.notices, a.message] };
  return reduce(s, a.event, a.data);
}

const EXAMPLES: Record<Mode, string> = {
  ask: "e.g. When did Python 2 reach end of life?",
  topic: "e.g. attention in transformers",
};

export default function Ask() {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("ask");
  const [scope, setScope] = useState(params.get("doc") ? "docs" : (params.get("collection") ?? ""));
  const [picked, setPicked] = useState<number[]>(params.get("doc") ? [Number(params.get("doc"))] : []);
  const [docs, setDocs] = useState<Doc[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [state, dispatch] = useReducer(reducer, initial);
  const [asked, setAsked] = useState<{ query: string; mode: Mode } | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    api.documents().then(setDocs).catch(() => {});
    api.collections().then(setCollections).catch(() => {});
    return () => abort.current?.abort();
  }, []);

  const running = state.phase !== "idle" && state.phase !== "done";
  const ready = docs.filter((d) => d.status === "ready");

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    const q = query.trim();
    if (!q || running) return;
    abort.current = new AbortController();
    setAsked({ query: q, mode });
    dispatch({ type: "start" });
    try {
      await api.ask(
        {
          query: q,
          mode,
          document_ids: scope === "docs" && picked.length ? picked : null,
          collection: scope && scope !== "docs" ? scope : null,
          check_conflicts: true,
        },
        (event, data) => dispatch({ type: "event", event, data }),
        abort.current.signal,
      );
    } catch (err) {
      const stopped = err instanceof DOMException && err.name === "AbortError";
      dispatch({ type: "fail", message: stopped ? "Stopped." : err instanceof Error ? err.message : "Something went wrong" });
    }
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const toggle = (id: number) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  return (
    <>
      <TopBar />
      <main className="page">
        <form className={`panel ask-box${asked ? " compact" : ""}`} onSubmit={submit}>
          {!asked && (
            <div className="hero">
              <h1>Ask your library</h1>
              <p className="muted">
                Answers come only from your documents, with every passage cited. When two documents disagree, you'll see both
                sides.
              </p>
            </div>
          )}
          <div className="seg" role="tablist" aria-label="Mode">
            {(["ask", "topic"] as Mode[]).map((m) => (
              <button key={m} type="button" role="tab" aria-selected={mode === m} className={mode === m ? "on" : ""} onClick={() => setMode(m)}>
                {m === "ask" ? "Ask a question" : "What do I know about…"}
              </button>
            ))}
          </div>
          <textarea
            aria-label={mode === "ask" ? "Question" : "Topic"}
            rows={asked ? 1 : 2}
            placeholder={EXAMPLES[mode]}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKey}
            maxLength={2000}
            autoFocus
          />
          <div className="ask-row">
            <label className="scope">
              <span className="muted small">Search in</span>
              <select
                value={scope}
                onChange={(e) => {
                  setScope(e.target.value);
                  if (params.size) setParams({}, { replace: true });
                }}
              >
                <option value="">Whole library ({ready.length})</option>
                {collections.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.documents})
                  </option>
                ))}
                <option value="docs">Chosen documents…</option>
              </select>
            </label>
            <div className="grow" />
            {running ? (
              <button type="button" className="btn" onClick={() => abort.current?.abort()}>
                Stop
              </button>
            ) : (
              <button className="btn btn-primary" disabled={!query.trim() || (scope === "docs" && !picked.length)}>
                {mode === "ask" ? "Ask" : "Summarise"}
              </button>
            )}
          </div>
          {scope === "docs" && (
            <div className="pick">
              {ready.map((d) => (
                <label key={d.id} className={picked.includes(d.id) ? "on" : ""}>
                  <input type="checkbox" checked={picked.includes(d.id)} onChange={() => toggle(d.id)} />
                  {d.title}
                </label>
              ))}
            </div>
          )}
        </form>

        {docs.length === 0 && !asked && (
          <p className="empty muted">
            Your library is empty. <Link to="/library">Add a PDF, a link or a note</Link> first.
          </p>
        )}

        {asked && (
          <>
            <h2 className="asked">{asked.query}</h2>
            <Result state={state} mode={asked.mode} />
          </>
        )}
      </main>
    </>
  );
}
