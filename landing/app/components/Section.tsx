import Inline from "./Inline";

export default function Section({
  id,
  kicker,
  title,
  intro,
  last = false,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  intro?: string;
  last?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className={last ? "" : "border-b"} style={{ borderColor: "var(--border)" }}>
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-8">
        <div className="max-w-xl">
          <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--accent)" }}>
            {kicker}
          </span>
          <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
          {intro && (
            <p className="prose-inline mt-4 text-base leading-relaxed" style={{ color: "var(--fg-muted)" }}>
              <Inline text={intro} />
            </p>
          )}
        </div>
        {children}
      </div>
    </section>
  );
}
