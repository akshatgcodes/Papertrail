// Shape of content.ts. Text fields render `backticks` as inline code.

export type Feature = { icon: string; title: string; body: string };

export type Shot = { src: string; alt: string; caption: string };

export type Step = { text: string; cmd?: string };

export type Site = {
  name: string;
  /** One letter for the logo square. */
  letter: string;
  title: string;
  description: string;
  /** Pills above the headline; the first one is highlighted. */
  meta: string[];
  headline: [string, string];
  intro: string;
  /** Main call to action: the app for web projects, install steps for CLIs. */
  primary: { label: string; href: string };
  repo: string;
  /** Shown under the buttons, e.g. the demo password. */
  note?: string;
  xfactor: { title: string; intro: string; features: Feature[] };
  preview: { intro: string; shots?: Shot[]; terminal?: string };
  stack: string[];
  concepts: { title: string; body: string }[];
  run: { title: string; intro: string; blocks: { title: string; steps: Step[] }[] };
  tagline: string;
};
