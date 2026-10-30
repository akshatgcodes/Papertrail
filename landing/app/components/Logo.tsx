import { site } from "../content";

export default function Logo({ size }: { size: number }) {
  return (
    <span
      className="flex shrink-0 items-center justify-center rounded-md font-bold"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.5,
        background: "var(--accent)",
        color: "var(--on-accent)",
      }}
    >
      {site.letter}
    </span>
  );
}
