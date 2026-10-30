import { site } from "../content";
import Inline from "./Inline";
import Section from "./Section";

export default function TechStack() {
  return (
    <Section id="stack" kicker="Under the hood" title="Key concepts & stack">
      <div className="mt-8 flex flex-wrap gap-2">
        {site.stack.map((b) => (
          <span key={b} className="rounded-md border px-3 py-1.5 font-mono text-sm font-medium" style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}>
            {b}
          </span>
        ))}
      </div>
      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {site.concepts.map((c) => (
          <div key={c.title} className="rounded-xl border p-5" style={{ borderColor: "var(--border)" }}>
            <h3 className="text-sm font-semibold">{c.title}</h3>
            <p className="prose-inline mt-1.5 text-[13px] leading-relaxed" style={{ color: "var(--fg-muted)" }}>
              <Inline text={c.body} />
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}
