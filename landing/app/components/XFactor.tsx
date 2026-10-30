import { site } from "../content";
import Inline from "./Inline";
import Section from "./Section";

export default function XFactor() {
  const { title, intro, features } = site.xfactor;
  return (
    <Section id="x-factor" kicker="The X factor" title={title} intro={intro}>
      <div className="mt-12 grid gap-5 md:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="rounded-2xl border p-6" style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}>
            <div
              className="flex h-10 w-10 items-center justify-center rounded-lg text-lg"
              style={{ background: "var(--accent-soft)", color: "var(--accent-fg)" }}
            >
              {f.icon}
            </div>
            <h3 className="mt-4 text-lg font-semibold">{f.title}</h3>
            <p className="prose-inline mt-2 text-sm leading-relaxed" style={{ color: "var(--fg-muted)" }}>
              <Inline text={f.body} />
            </p>
          </div>
        ))}
      </div>
    </Section>
  );
}
