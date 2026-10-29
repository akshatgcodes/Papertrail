import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, pageUrl } from "../api";
import { ago, KindBadge } from "../components/Kind";
import TopBar from "../components/TopBar";
import { around } from "../lib/answer";
import type { DocFull, Passage } from "../types";

export default function DocumentPage() {
  const { id } = useParams();
  const docId = Number(id);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [doc, setDoc] = useState<DocFull | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const load = useCallback(() => api.document(docId).then(setDoc).catch((e) => setError(e.message)), [docId]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    if (doc?.status !== "processing") return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [doc?.status, load]);

  if (error) {
    return (
      <>
        <TopBar />
        <main className="page">
          <p className="error">{error}</p>
          <Link to="/library">Back to the library</Link>
        </main>
      </>
    );
  }
  if (!doc) return <TopBar />;

  const activeId = Number(params.get("p")) || null;
  const active = doc.passages.find((p) => p.id === activeId) ?? null;
  const select = (p: Passage | null) => setParams(p ? { p: String(p.id) } : {}, { replace: true });

  const save = async (patch: { title?: string; collection?: string; content?: string }) => {
    try {
      await api.update(doc.id, patch);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save");
    }
  };
  const remove = async () => {
    if (!confirm(`Delete "${doc.title}"? Its passages leave the index too.`)) return;
    await api.remove(doc.id);
    navigate("/library");
  };

  return (
    <>
      <TopBar />
      <main className="page">
        <p className="muted small">
          <Link to="/library">Library</Link> · <KindBadge kind={doc.kind} /> · added {ago(doc.created_at)}
          {doc.source_url && (
            <>
              {" · "}
              <a href={doc.source_url} target="_blank" rel="noreferrer">
                {new URL(doc.source_url).hostname}
              </a>
            </>
          )}
        </p>
        <div className="doc-head">
          <EditableTitle value={doc.title} onSave={(title) => save({ title })} />
          <div className="doc-actions">
            <Link className="btn btn-sm btn-primary" to={`/?doc=${doc.id}`}>
              Ask about this
            </Link>
            {doc.kind === "note" && (
              <button className="btn btn-sm" onClick={() => setEditing((x) => !x)}>
                {editing ? "Cancel" : "Edit"}
              </button>
            )}
            <button className="btn btn-sm" onClick={() => api.reindex(doc.id).then(load)}>
              Re-index
            </button>
            <button className="btn btn-sm danger" onClick={remove}>
              Delete
            </button>
          </div>
        </div>
        <div className="doc-meta">
          <CollectionField value={doc.collection} onSave={(collection) => save({ collection })} />
          <span className="muted small">
            {doc.status === "ready" && `${doc.passages.length} passages`}
            {doc.pages ? ` · ${doc.pages} pages` : ""}
            {doc.chars ? ` · ${doc.chars.toLocaleString()} characters` : ""}
          </span>
          {doc.status === "processing" && <span className="tag pulse">Indexing…</span>}
        </div>
        {doc.status === "failed" && <p className="notice">Indexing failed: {doc.error}</p>}

        {editing ? (
          <NoteEditor
            initial={doc.content}
            onSave={async (content) => {
              await save({ content });
              setEditing(false);
            }}
          />
        ) : doc.kind === "pdf" ? (
          <PdfView doc={doc} active={active} onSelect={select} />
        ) : (
          <TextView doc={doc} active={active} onSelect={select} />
        )}
      </main>
    </>
  );
}

function EditableTitle({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  const commit = () => {
    const v = draft.trim();
    if (v && v !== value) onSave(v);
    else setDraft(value);
  };
  return (
    <input
      className="title-input"
      value={draft}
      aria-label="Title"
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
      maxLength={500}
    />
  );
}

function CollectionField({ value, onSave }: { value: string; onSave: (v: string) => void }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => setDraft(value), [value]);
  return (
    <label className="scope">
      <span className="muted small">Collection</span>
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => draft.trim() !== value && onSave(draft)}
        onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
        maxLength={80}
      />
    </label>
  );
}

function NoteEditor({ initial, onSave }: { initial: string; onSave: (v: string) => void }) {
  const [text, setText] = useState(initial);
  return (
    <div className="panel note-form">
      <textarea rows={18} value={text} onChange={(e) => setText(e.target.value)} aria-label="Note" />
      <div>
        <button className="btn btn-primary" disabled={!text.trim() || text === initial} onClick={() => onSave(text)}>
          Save and re-index
        </button>
      </div>
    </div>
  );
}

type ViewProps = { doc: DocFull; active: Passage | null; onSelect: (p: Passage | null) => void };

function Outline({ doc, active, onSelect, passages }: ViewProps & { passages: Passage[] }) {
  return (
    <ol className="outline">
      {passages.map((p) => (
        <li key={p.id}>
          <button className={active?.id === p.id ? "on" : ""} onClick={() => onSelect(active?.id === p.id ? null : p)}>
            <span className="muted small">{p.idx + 1}</span> {p.heading || p.text.slice(0, 70)}
          </button>
        </li>
      ))}
      {doc.passages.length === 0 && <li className="muted small">No passages yet.</li>}
    </ol>
  );
}

function TextView({ doc, active, onSelect }: ViewProps) {
  const mark = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    mark.current?.scrollIntoView({ block: "center" });
  }, [active?.id]);
  const hasRange = active && active.start !== null && active.end !== null;
  const [before, inside, after] = hasRange ? around(doc.content, active.start!, active.end!) : [doc.content, "", ""];
  return (
    <div className="doc-body">
      <aside className="doc-side">
        <p className="label">Passages</p>
        <Outline doc={doc} active={active} onSelect={onSelect} passages={doc.passages} />
      </aside>
      <article className="panel doc-text">
        {before}
        {inside && (
          <mark ref={mark} className="hit">
            {inside}
          </mark>
        )}
        {after}
      </article>
    </div>
  );
}

function PdfView({ doc, active, onSelect }: ViewProps) {
  const [page, setPage] = useState(active?.page ?? 0);
  useEffect(() => {
    if (active?.page !== null && active?.page !== undefined) setPage(active.page);
  }, [active?.id, active?.page]);
  const pages = doc.pages ?? 0;
  const onPage = doc.passages.filter((p) => p.page === page);
  const highlight = active?.page === page ? active.id : undefined;
  return (
    <div className="doc-body">
      <aside className="doc-side">
        <p className="label">Passages on page {page + 1}</p>
        <Outline doc={doc} active={active} onSelect={onSelect} passages={onPage} />
      </aside>
      <div className="pdf">
        <div className="pager">
          <button className="btn btn-sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
            ← Prev
          </button>
          <span className="small">
            Page {page + 1} of {pages}
          </span>
          <button className="btn btn-sm" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>
            Next →
          </button>
        </div>
        {pages > 0 && <img className="page-img" src={pageUrl(doc.id, page, highlight)} alt={`Page ${page + 1}`} />}
        {active && active.page === page && <p className="panel hit-text small">{active.text}</p>}
      </div>
    </div>
  );
}
