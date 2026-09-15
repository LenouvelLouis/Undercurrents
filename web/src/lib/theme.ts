export type Accent = "magenta" | "teal";

export const accentText: Record<Accent, string> = {
  magenta: "text-magenta",
  teal: "text-teal",
};

export const accentBorder: Record<Accent, string> = {
  magenta: "border-magenta",
  teal: "border-teal",
};

export const accentBg: Record<Accent, string> = {
  magenta: "bg-magenta",
  teal: "bg-teal",
};

export const accentBgTint: Record<Accent, string> = {
  magenta: "bg-magenta/10",
  teal: "bg-teal/10",
};

export const accentCardTint: Record<Accent, string> = {
  magenta: "bg-magenta/15 border-magenta/40",
  teal: "bg-teal/15 border-teal/40",
};
