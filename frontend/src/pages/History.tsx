import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ago } from "../components/Kind";
import TopBar from "../components/TopBar";
import type { QuerySummary } from "../types";

const STATUS: Record<string, string> = {
  answered: "",
  not_found: "Not in library",
  declined: "No answer",
  error: "Failed",
  stopped: "Stopped",
};

export default function History() {
  const [items, setItems] = useState<QuerySummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.queries().then(setItems).catch((e) => setError(e.message));
  }, []);

  const remove = async (id: number) => {
    await api.removeQuery(id);
    setItems((xs) => xs?.filter((x) => x.id !== id) ?? null);
  };

  return (
    <>
      <TopBar />
      <main className="page narrow">
        <h1>History</h1>
        <p className="muted">Every question is saved with its answer, passages and conflicts.</p>
        {error && <p className="error">{error}</p>}
        {items?.length === 0 && (
          <p className="empty muted">
            Nothing yet. <Link to="/">Ask something</Link>.
          </p>
        )}
        <ul className="rows">
          {items?.map((q) => (
            <li key={q.id} className="row">
              <span className={`mode mode-${q.mode}`}>{q.mode === "topic" ? "Topic" : "Q"}</span>
              <Link to={`/q/${q.id}`} className="row-title">
                {q.text}
              </Link>
              {q.conflict_count > 0 && (
                <span className="tag warn">
                  {q.conflict_count} conflict{q.conflict_count > 1 ? "s" : ""}
                </span>
              )}
              {STATUS[q.status] && <span className="tag">{STATUS[q.status]}</span>}
              <span className="muted small nowrap">{ago(q.created_at)}</span>
              <button className="link-btn small" onClick={() => remove(q.id)} aria-label={`Delete "${q.text}"`}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
