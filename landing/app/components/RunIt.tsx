import { site } from "../content";
import Inline from "./Inline";
import Section from "./Section";

export default function RunIt() {
  const { title, intro, blocks } = site.run;
  return (
    <Section id="run-it" kicker="Run it" title={title} intro={intro} last>
      <div className={`mt-8 grid gap-5 ${blocks.length > 1 ? "lg:grid-cols-2" : "max-w-2xl"}`}>
        {blocks.map((b) => (
          <div key={b.title} className="min-w-0 rounded-xl border p-5" style={{ borderColor: "var(--border)" }}>
            <h3 className="text-sm font-bold" style={{ color: "var(--accent-fg)" }}>
              {b.title}
            </h3>
            <ol className="mt-4 flex flex-col gap-4">
              {b.steps.map((s, i) => (
                <li key={i} className="flex gap-3">
                  <span
                    className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
                    style={{ background: "var(--accent-soft)", color: "var(--accent-fg)" }}
                  >
                    {i + 1}
                  </span>
                  <div className="prose-inline min-w-0 flex-1 text-sm leading-relaxed" style={{ color: "var(--fg-muted)" }}>
                    <Inline text={s.text} />
                    {s.cmd && (
                      <pre
                        className="mt-1.5 overflow-x-auto rounded-md border px-3 py-2 font-mono text-[12.5px]"
                        style={{ borderColor: "var(--border)", background: "var(--code-bg)", color: "var(--fg)" }}
                      >
                        <code>{s.cmd}</code>
                      </pre>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    </Section>
  );
}
