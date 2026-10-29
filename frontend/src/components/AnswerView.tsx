import { Fragment } from "react";
import { Link } from "react-router-dom";
import { blocks, bySource, type Inline } from "../lib/answer";
import type { Confidence, Conflict, Source } from "../types";
import { KindBadge } from "./Kind";

export function sourceLink(s: Source) {
  return `/d/${s.document_id}?p=${s.chunk_id}`;
}

function Pieces({ items, sources, onCite }: { items: Inline[]; sources: Source[]; onCite: (n: number) => void }) {
  return (
    <>
      {items.map((x, i) => {
        if (x.type === "text") return <Fragment key={i}>{x.text}</Fragment>;
        if (x.type === "bold") return <strong key={i}>{x.text}</strong>;
        if (x.type === "code") return <code key={i}>{x.text}</code>;
        const s = sources.find((y) => y.n === x.n);
        return (
          <button
            key={i}
            type="button"
            className="cite"
            title={s ? `${s.title}${s.heading ? ` › ${s.heading}` : ""}` : "Not one of the passages"}
            onClick={() => onCite(x.n)}
          >
            {x.n}
          </button>
        );
      })}
    </>
  );
}

export function AnswerText({ text, sources, onCite }: { text: string; sources: Source[]; onCite: (n: number) => void }) {
  return (
    <div className="answer-text">
      {blocks(text).map((b, i) =>
        b.type === "heading" ? (
          <h3 key={i}>
            <Pieces items={b.inline} sources={sources} onCite={onCite} />
          </h3>
        ) : b.type === "list" ? (
          <ul key={i}>
            {b.items.map((item, j) => (
              <li key={j}>
                <Pieces items={item} sources={sources} onCite={onCite} />
              </li>
            ))}
          </ul>
        ) : (
          <p key={i}>
            <Pieces items={b.inline} sources={sources} onCite={onCite} />
          </p>
        ),
      )}
    </div>
  );
}

export function ConfidenceBadge({ c }: { c: Confidence }) {
  const label = { high: "Strong match", medium: "Partial match", low: "Weak match" }[c.level];
  return (
    <span className={`conf conf-${c.level}`} title={`Best passage similarity ${c.score.toFixed(2)} (cut-off ${c.threshold})`}>
      {label}
    </span>
  );
}

export function Sources({
  sources,
  active,
  onPick,
  answered,
}: {
  sources: Source[];
  active: number | null;
  onPick: (n: number) => void;
  answered: boolean;
}) {
  const groups = bySource(sources);
  return (
    <div className="sources">
      <p className="label">
        {sources.length} passage{sources.length === 1 ? "" : "s"} from {groups.length} document{groups.length === 1 ? "" : "s"}
      </p>
      {groups.map((g) => (
        <section key={g.document_id} className="source-group">
          <header>
            <KindBadge kind={g.kind} />
            <Link to={`/d/${g.document_id}`} className="source-title">
              {g.title}
            </Link>
          </header>
          {g.sources.map((s) => (
            <article
              key={s.n}
              id={`src-${s.n}`}
              className={`passage${s.cited || !answered ? " cited" : ""}${active === s.n ? " active" : ""}`}
              onClick={() => onPick(s.n)}
            >
              <div className="passage-meta">
                <span className="num">{s.n}</span>
                <span className="muted small">
                  {s.heading || (s.page !== null ? `Page ${s.page + 1}` : "")}
                  {s.heading && s.page !== null ? ` · page ${s.page + 1}` : ""}
                </span>
                {answered && !s.cited && <span className="muted small not-cited">not cited</span>}
                <Link to={sourceLink(s)} className="small open" onClick={(e) => e.stopPropagation()}>
                  Open
                </Link>
              </div>
              <p className={active === s.n ? "" : "clamp"}>{s.text}</p>
            </article>
          ))}
        </section>
      ))}
    </div>
  );
}

export function Conflicts({ items, sources, onPick }: { items: Conflict[]; sources: Source[]; onPick: (n: number) => void }) {
  const side = (n: number, claim: string, tag: string) => {
    const s = sources.find((x) => x.n === n);
    return (
      <button type="button" className="claim" onClick={() => onPick(n)}>
        <span className="claim-tag">{tag}</span>
        <span className="claim-text">{claim || s?.text.slice(0, 160)}</span>
        <span className="muted small">
          {s?.title ?? "?"} <span className="cite static">{n}</span>
        </span>
      </button>
    );
  };
  return (
    <section className="conflicts">
      <h2>
        <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
          <path d="M8 1.5 15 14H1z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
          <path d="M8 6v3.6M8 11.6v.4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
        {items.length === 1 ? "Your documents disagree" : `Your documents disagree on ${items.length} points`}
      </h2>
      {items.map((c, i) => (
        <article key={i} className="conflict">
          <p className="conflict-topic">{c.topic}</p>
          <div className="claims">
            {side(c.a, c.claim_a, "A")}
            {side(c.b, c.claim_b, "B")}
          </div>
          {c.note && <p className="muted small">{c.note}</p>}
        </article>
      ))}
    </section>
  );
}
