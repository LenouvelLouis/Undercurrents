// Real figures from /api/stats/overview, 2026-09-20.
export const overview = {
  concerts: 767,
  yearsStart: 2008,
  yearsEnd: 2026,
  venues: 556,
  countries: 39,
  setlistAccuracy: 0.91,
  clusters: 43,
}

// The two halves of the product and what sits in each. No 01..13 numbering: the order of
// these pages carries no information, and numbering it implies a sequence that is not there.
export const sections = [
  {
    key: "predictions",
    label: "Predictions",
    accent: "violet",
    blurb: "What the next night is likely to hold, each figure beside the baseline it had to beat.",
    pages: [
      "Next Setlist", "Running Order", "Concert Length", "Encore",
      "Coming Back", "Song Role", "Next Date", "Next Country",
    ],
  },
  {
    key: "analysis",
    label: "Analysis",
    accent: "ember",
    blurb: "What eighteen years on the road actually did, read straight off the record.",
    pages: [
      "Venue Map", "Setlist Trend", "Cluster Explorer", "Transition Graph", "Anecdotes",
      "Tours", "Covers & Encores", "Song Map", "Heatmaps", "Models", "Song Explorer",
      "Night Notes", "Sound Profile",
    ],
  },
] as const
