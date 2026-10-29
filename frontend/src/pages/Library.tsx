import { useCallback, useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { ago, KindBadge } from "../components/Kind";
import TopBar from "../components/TopBar";
import type { Collection, Doc, Stats } from "../types";

type Tab = "files" | "url" | "note";
const ACCEPT = ".pdf,.md,.markdown,.txt";

export default function Library() {
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [d, c, s] = await Promise.all([api.documents(), api.collections(), api.stats()]);
      setDocs(d);
      setCollections(c);
      setStats(s);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load the library");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Indexing happens after the upload returns; poll until nothing is processing
  const processing = docs?.some((d) => d.status === "processing");
  useEffect(() => {
    if (!processing) return;
    const t = setInterval(load, 1500);
    return () => clearInterval(t);
  }, [processing, load]);

  const q = search.trim().toLowerCase();
  const shown = (docs ?? []).filter((d) => (!filter || d.collection === filter) && (!q || d.title.toLowerCase().includes(q)));

  return (
    <>
      <TopBar />
      <main className="page">
        <div className="lib-head">
          <div>
            <h1>Library</h1>
            {stats && (
              <p className="muted">
                {stats.documents} document{stats.documents === 1 ? "" : "s"} · {stats.passages.toLocaleString()} passages
                {stats.processing > 0 && ` · ${stats.processing} indexing`}
              </p>
            )}
          </div>
        </div>
        <AddPanel collections={collections} onAdded={load} />
        {error && <p className="error">{error}</p>}

        {docs && docs.length > 0 && (
          <div className="lib-tools">
            <div className="chips" role="group" aria-label="Collection">
              <button className={!filter ? "chip on" : "chip"} onClick={() => setFilter("")}>
                All <span>{docs.length}</span>
              </button>
              {collections.map((c) => (
                <button key={c.name} className={filter === c.name ? "chip on" : "chip"} onClick={() => setFilter(c.name)}>
                  {c.name} <span>{c.documents}</span>
                </button>
              ))}
            </div>
            <input className="search" type="search" placeholder="Filter by title" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        )}

        {docs?.length === 0 && <p className="empty muted">Nothing here yet. Add a PDF, a link or a note above.</p>}
        <ul className="rows">
          {shown.map((d) => (
            <li key={d.id} className="row">
              <KindBadge kind={d.kind} />
              <Link to={`/d/${d.id}`} className="row-title">
                {d.title}
              </Link>
              <span className="tag">{d.collection}</span>
              {d.status === "processing" && <span className="tag pulse">Indexing…</span>}
              {d.status === "failed" && (
                <span className="tag bad" title={d.error}>
                  Failed
                </span>
              )}
              {d.status === "ready" && (
                <span className="muted small nowrap">
                  {d.pages ? `${d.pages} pages · ` : ""}
                  {d.chunks} passages
                </span>
              )}
              <span className="muted small nowrap">{ago(d.created_at)}</span>
            </li>
          ))}
        </ul>
        {docs && docs.length > 0 && shown.length === 0 && <p className="empty muted">No documents match.</p>}
      </main>
    </>
  );
}

function AddPanel({ collections, onAdded }: { collections: Collection[]; onAdded: () => void }) {
  const [tab, setTab] = useState<Tab>("files");
  const [collection, setCollection] = useState("");
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onAdded();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "That didn't work");
      return false;
    } finally {
      setBusy(false);
    }
  };

  const sendFiles = (files: File[]) => files.length && run(() => api.upload(files, collection));
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    sendFiles([...e.dataTransfer.files]);
  };
  const addUrl = async (e: FormEvent) => {
    e.preventDefault();
    if (await run(() => api.addUrl(url, collection))) setUrl("");
  };
  const addNote = async (e: FormEvent) => {
    e.preventDefault();
    if (await run(() => api.addNote(title, note, collection))) {
      setTitle("");
      setNote("");
    }
  };

  return (
    <section className="panel add">
      <div className="add-head">
        <div className="seg" role="tablist" aria-label="Add">
          {(
            [
              ["files", "Upload files"],
              ["url", "Save a link"],
              ["note", "Write a note"],
            ] as [Tab, string][]
          ).map(([t, label]) => (
            <button key={t} type="button" role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
              {label}
            </button>
          ))}
        </div>
        <label className="scope">
          <span className="muted small">Collection</span>
          <input list="collections" placeholder="General" value={collection} onChange={(e) => setCollection(e.target.value)} maxLength={80} />
          <datalist id="collections">
            {collections.map((c) => (
              <option key={c.name} value={c.name} />
            ))}
          </datalist>
        </label>
      </div>

      {tab === "files" && (
        <div
          className={`drop${drag ? " over" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
        >
          <p>
            <strong>Drop PDFs, Markdown or text files</strong>
          </p>
          <p className="muted small">Up to 20 MB each. Scanned PDFs without a text layer can't be read.</p>
          <button type="button" className="btn" disabled={busy} onClick={() => input.current?.click()}>
            {busy ? "Uploading…" : "Choose files"}
          </button>
          <input
            ref={input}
            type="file"
            multiple
            accept={ACCEPT}
            hidden
            onChange={(e) => {
              sendFiles([...(e.target.files ?? [])]);
              e.target.value = "";
            }}
          />
        </div>
      )}
      {tab === "url" && (
        <form className="inline-form" onSubmit={addUrl}>
          <input type="url" placeholder="https://en.wikipedia.org/wiki/…" value={url} onChange={(e) => setUrl(e.target.value)} required aria-label="Link" />
          <button className="btn btn-primary" disabled={busy || !url.trim()}>
            {busy ? "Fetching…" : "Save"}
          </button>
        </form>
      )}
      {tab === "note" && (
        <form className="note-form" onSubmit={addNote}>
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={500} aria-label="Title" />
          <textarea
            rows={6}
            placeholder={"Markdown works: # headings split the note into sections.\n\nWhatever you write here can be cited in answers."}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            required
            aria-label="Note"
          />
          <div>
            <button className="btn btn-primary" disabled={busy || !title.trim() || !note.trim()}>
              {busy ? "Saving…" : "Save note"}
            </button>
          </div>
        </form>
      )}
      {error && <p className="error small">{error}</p>}
    </section>
  );
}
