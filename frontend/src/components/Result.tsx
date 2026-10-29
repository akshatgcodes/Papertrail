import { useState } from "react";
import { Link } from "react-router-dom";
import type { AskState } from "../lib/answer";
import type { Mode } from "../types";
import { AnswerText, ConfidenceBadge, Conflicts, Sources } from "./AnswerView";

const EMPTY: Record<string, { title: string; body: string }> = {
  not_found: {
    title: "Nothing in your library covers this",
    body: "No passage came close enough to the question, so no answer was written. Try other words, a wider scope, or add a document that covers it.",
  },
  declined: {
    title: "The passages found don't answer it",
    body: "Some passages looked related, but the model found no answer in them. They're listed so you can check.",
  },
  error: { title: "The answer couldn't be written", body: "The passages were found, but the model call failed." },
  stopped: { title: "Stopped", body: "The answer was stopped before it finished." },
};

export default function Result({ state, mode }: { state: AskState; mode: Mode }) {
  const [active, setActive] = useState<number | null>(null);
  const pick = (n: number) => {
    setActive(n);
    document.getElementById(`src-${n}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  const text = state.answer || (state.status ? "" : state.draft.replace(/【\s*(\d+)(?:\s*†[^】]*)?】/g, "[$1]"));
  const empty = state.status && state.status !== "answered" ? EMPTY[state.status] : null;

  return (
    <div className="result">
      <div className="result-main">
        <div className="panel answer">
          <div className="answer-head">
            <span className="label">{mode === "topic" ? "What your library says" : "Answer"}</span>
            {state.confidence && state.sources.length > 0 && <ConfidenceBadge c={state.confidence} />}
            {state.ms !== null && <span className="muted small">{(state.ms / 1000).toFixed(1)} s</span>}
          </div>
          {state.phase === "retrieving" && <p className="muted pulse">Searching your library…</p>}
          {text && <AnswerText text={text} sources={state.sources} onCite={pick} />}
          {state.phase === "writing" && !state.status && !text && <p className="muted pulse">Reading {state.sources.length} passages…</p>}
          {empty && (
            <div className="empty-answer">
              <p>
                <strong>{empty.title}</strong>
              </p>
              <p className="muted small">{empty.body}</p>
            </div>
          )}
          {state.notices.map((n, i) => (
            <p key={i} className="notice small">
              {n}
            </p>
          ))}
          {state.phase === "checking" && <p className="muted small pulse">Checking the cited documents against each other…</p>}
          {state.phase === "done" && state.status === "answered" && state.pairs !== null && state.conflicts.length === 0 && (
            <p className="muted small agree">
              {state.pairs === 0
                ? "The cited passages don't overlap enough to compare."
                : `No disagreements found between the cited documents (${state.pairs} passage pair${state.pairs === 1 ? "" : "s"} checked).`}
            </p>
          )}
          {state.queryId !== null && (
            <p className="small">
              <Link to={`/q/${state.queryId}`}>Permalink</Link>
            </p>
          )}
        </div>
        {state.conflicts.length > 0 && <Conflicts items={state.conflicts} sources={state.sources} onPick={pick} />}
      </div>
      {state.sources.length > 0 && (
        <aside className="result-side">
          <Sources sources={state.sources} active={active} onPick={setActive} answered={state.status === "answered"} />
        </aside>
      )}
    </div>
  );
}
