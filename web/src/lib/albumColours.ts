// One colour per record, from the mood of each sleeve. Shared by every chart that colours
// songs by album, so a record looks the same everywhere.
export const ALBUM_COLOURS: Record<string, string> = {
  Innerspeaker: "#e7b24a",
  Lonerism: "#f0673f",
  Currents: "#b04be0",
  "The Slow Rush": "#e0855a",
  Deadbeat: "#5fc7c0",
  "Singles, EPs and B-sides": "#cdbfe8",
  "Unreleased or live-only": "#7c6e86",
  Covers: "#4f4658",
};

export const albumColour = (name: string | null | undefined) => (name && ALBUM_COLOURS[name]) || "#cdbfe8";
