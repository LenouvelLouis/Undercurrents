export type Accent = "violet" | "ember";

export const accentText: Record<Accent, string> = {
  violet: "text-violet",
  ember: "text-ember",
};

export const accentBorder: Record<Accent, string> = {
  violet: "border-violet",
  ember: "border-ember",
};

export const accentBg: Record<Accent, string> = {
  violet: "bg-violet",
  ember: "bg-ember",
};

export const accentBgTint: Record<Accent, string> = {
  violet: "bg-violet/10",
  ember: "bg-ember/10",
};

export const accentCardTint: Record<Accent, string> = {
  violet: "bg-violet/15 border-violet/40",
  ember: "bg-ember/15 border-ember/40",
};
