import { site } from "../content";
import Inline from "./Inline";

export default function Hero() {
  return (
    <section id="top" className="bg-noise border-b" style={{ borderColor: "var(--border)" }}>
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-8 sm:py-28">
        <div className="flex flex-wrap items-center gap-2 text-xs font-semibold tracking-wide" style={{ color: "var(--fg-muted)" }}>
          {site.meta.map((m, i) =>
            i === 0 ? (
              <span key={m} className="rounded-full px-2.5 py-1" style={{ background: "var(--accent-soft)", color: "var(--accent-fg)" }}>
                ● {m}
              </span>
            ) : (
              <span key={m} className="flex items-center gap-2">
                {i > 1 && <span>·</span>}
                {m}
              </span>
            ),
          )}
        </div>

        <h1 className="mt-6 max-w-3xl text-4xl leading-[1.1] font-bold tracking-tight sm:text-6xl">
          {site.headline[0]} <span style={{ color: "var(--accent)" }}>{site.headline[1]}</span>
        </h1>

        <p className="prose-inline mt-6 max-w-xl text-lg leading-relaxed" style={{ color: "var(--fg-muted)" }}>
          <Inline text={site.intro} />
        </p>

        <div className="mt-9 flex flex-wrap gap-3">
          <a
            href={site.primary.href}
            className="rounded-lg px-5 py-2.5 text-sm font-semibold transition-transform hover:scale-[1.02]"
            style={{ background: "var(--accent)", color: "var(--on-accent)" }}
          >
            {site.primary.label}
          </a>
          <a href={site.repo} className="rounded-lg border px-5 py-2.5 text-sm font-semibold transition-colors hover:opacity-80" style={{ borderColor: "var(--border)" }}>
            View the code
          </a>
          <a href="#x-factor" className="rounded-lg border px-5 py-2.5 text-sm font-semibold transition-colors hover:opacity-80" style={{ borderColor: "var(--border)" }}>
            See the X factor
          </a>
        </div>

        {site.note && (
          <p className="prose-inline mt-5 text-sm" style={{ color: "var(--fg-muted)" }}>
            <Inline text={site.note} />
          </p>
        )}
      </div>
    </section>
  );
}
