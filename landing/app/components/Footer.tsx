import { site } from "../content";
import Logo from "./Logo";

export default function Footer() {
  return (
    <footer className="border-t" style={{ borderColor: "var(--border)" }}>
      <div
        className="mx-auto flex max-w-5xl flex-col gap-3 px-4 py-8 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-8"
        style={{ color: "var(--fg-muted)" }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <Logo size={24} />
          <span className="font-semibold" style={{ color: "var(--fg)" }}>
            {site.name}
          </span>
          <span>— {site.tagline}</span>
        </div>
        <div className="flex gap-4">
          <a href={site.repo} className="hover:opacity-80">GitHub</a>
          <a href="https://akshatgcodes.in" className="hover:opacity-80">Akshat Gupta</a>
          <span>GPLv3</span>
        </div>
      </div>
    </footer>
  );
}
