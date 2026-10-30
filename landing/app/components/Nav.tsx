import { site } from "../content";
import Logo from "./Logo";

export default function Nav() {
  return (
    <header
      className="sticky top-0 z-50 border-b backdrop-blur"
      style={{
        borderColor: "var(--border)",
        background: "color-mix(in srgb, var(--bg) 85%, transparent)",
      }}
    >
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3.5 sm:px-8">
        <a href="#top" className="flex items-center gap-2 font-semibold">
          <Logo size={28} />
          <span>{site.name}</span>
        </a>
        <nav className="hidden items-center gap-6 text-sm font-medium md:flex" style={{ color: "var(--fg-muted)" }}>
          <a href="#x-factor" className="transition-colors hover:opacity-80">X Factor</a>
          <a href="#preview" className="transition-colors hover:opacity-80">Preview</a>
          <a href="#stack" className="transition-colors hover:opacity-80">Stack</a>
          <a href="#run-it" className="transition-colors hover:opacity-80">Run it</a>
          <a href={site.repo} className="transition-colors hover:opacity-80">GitHub</a>
        </nav>
        <a
          href={site.primary.href}
          className="shrink-0 rounded-md px-3.5 py-1.5 text-sm font-semibold transition-transform hover:scale-[1.03]"
          style={{ background: "var(--accent)", color: "var(--on-accent)" }}
        >
          {site.primary.label}
        </a>
      </div>
    </header>
  );
}
