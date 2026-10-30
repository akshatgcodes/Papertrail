/* eslint-disable @next/next/no-img-element -- static export, screenshots are already sized */
import { site } from "../content";
import Section from "./Section";

function Frame({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="overflow-hidden rounded-xl border shadow-sm" style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}>
      <div className="flex items-center gap-3 border-b px-4 py-2.5" style={{ borderColor: "var(--border)", background: "var(--bg-sunken)" }}>
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#f87171" }} />
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#fbbf24" }} />
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: "#4ade80" }} />
        </div>
        <span className="truncate font-mono text-xs" style={{ color: "var(--fg-muted)" }}>
          {label}
        </span>
      </div>
      {children}
    </div>
  );
}

export default function Preview() {
  const { intro, shots = [], terminal } = site.preview;
  const [main, ...rest] = shots;
  return (
    <Section id="preview" kicker="Preview" title="What it looks like" intro={intro}>
      {terminal && (
        <div className="mt-10">
          <Frame label="zsh">
            <pre className="overflow-x-auto px-4 py-4 font-mono text-[12.5px] leading-relaxed" style={{ background: "var(--code-bg)" }}>
              <code>{terminal}</code>
            </pre>
          </Frame>
        </div>
      )}
      {main && (
        <figure className="mt-10">
          <Frame label={main.caption}>
            <img src={main.src} alt={main.alt} className="block w-full" />
          </Frame>
        </figure>
      )}
      {rest.length > 0 && (
        <div className={`mt-6 grid gap-5 ${rest.length > 1 ? "md:grid-cols-2" : ""}`}>
          {rest.map((s) => (
            <figure key={s.src}>
              <Frame label={s.caption}>
                <img src={s.src} alt={s.alt} className="block w-full" />
              </Frame>
            </figure>
          ))}
        </div>
      )}
    </Section>
  );
}
