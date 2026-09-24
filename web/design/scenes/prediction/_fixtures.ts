// Real values from data/models/encore_backtest.json and /api/predictions/encore, 2026-09-20.

export interface Candidate {
  song: string
  probability: number
  encores: number
  plays: number
}

export interface Method {
  key: string
  name: string
  validation: number
  folds: number[]
  test: number
  chosen: boolean
}

export const candidates: Candidate[] = [
  { song: "End of Summer", probability: 1.0, encores: 64, plays: 65 },
  { song: "The Less I Know the Better", probability: 1.0, encores: 145, plays: 292 },
  { song: "My Old Ways", probability: 0.9926, encores: 48, plays: 63 },
  { song: "Dracula", probability: 0.9802, encores: 11, plays: 67 },
  { song: "New Person, Same Old Mistakes", probability: 0.44, encores: 101, plays: 249 },
  { song: "One More Hour", probability: 0.25, encores: 41, plays: 45 },
  { song: "Eventually", probability: 0.19, encores: 3, plays: 301 },
  { song: "Nangs", probability: 0.19, encores: 1, plays: 226 },
]

export const methods: Method[] = [
  {
    key: "model",
    name: "Logistic regression on encore history",
    validation: 0.83,
    folds: [0.9136, 0.8025, 0.7738],
    test: 0.884,
    chosen: true,
  },
  {
    key: "recent",
    name: "Whatever was encored in the last 10 shows",
    validation: 0.8139,
    folds: [0.9012, 0.8025, 0.7381],
    test: 0.9171,
    chosen: false,
  },
  {
    key: "lifetime",
    name: "The most encored songs of all time",
    validation: 0.148,
    folds: [0.3951, 0.037, 0.0119],
    test: 0.2431,
    chosen: false,
  },
]

export const accuracy = {
  precision: 0.884,
  encoreSlots: 181,
  testShows: 60,
  validationFolds: 3,
  validationShows: 120,
  marginOverNextBest: -0.0331,
}
