import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { ago } from "../components/Kind";
import Result from "../components/Result";
import TopBar from "../components/TopBar";
import { initial, type AskState } from "../lib/answer";
import type { Confidence, QueryFull } from "../types";

export default function QueryPage() {
  const { id } = useParams();
  const [q, setQ] = useState<QueryFull | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.query(Number(id)).then(setQ).catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <>
        <TopBar />
        <main className="page">
          <p className="error">{error}</p>
        </main>
      </>
    );
  }
  if (!q) return <TopBar />;

  const state: AskState = {
    ...initial,
    phase: "done",
    sources: q.sources,
    confidence: "level" in q.confidence ? (q.confidence as Confidence) : null,
    answer: q.answer,
    status: q.status,
    conflicts: q.conflicts,
    ms: q.ms,
  };
  const scope = q.scope.collection ? `in ${q.scope.collection}` : q.scope.document_ids ? `in ${q.scope.document_ids.length} chosen documents` : "";
  return (
    <>
      <TopBar />
      <main className="page">
        <p className="muted small">
          <Link to="/history">History</Link> · {ago(q.created_at)} {scope} {q.model && `· ${q.model}`}
        </p>
        <h2 className="asked">{q.text}</h2>
        <Result state={state} mode={q.mode} />
      </main>
    </>
  );
}
