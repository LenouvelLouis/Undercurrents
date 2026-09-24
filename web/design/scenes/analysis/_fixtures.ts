// Real values, read out of data/undercurrents.db on 2026-09-20. Frames never call the
// network; these are the shapes the API already returns from /api/analysis/night-notes.

export interface ShowFormat { name: string; shows: number; songs: number }
export interface Guest { guest: string; song: string; city: string; date: string }
export interface NoteFlag { key: string; label: string; count: number }
export interface Tease { title: string; count: number }

export const formats: ShowFormat[] = [
  { name: "Main Stage", shows: 60, songs: 1008 },
  { name: "B-Stage", shows: 56, songs: 134 },
  { name: "Stage B", shows: 7, songs: 14 },
  { name: "Encore", shows: 3, songs: 5 },
  { name: "Acoustic", shows: 2, songs: 9 },
  { name: "Stage A", shows: 1, songs: 17 },
  { name: "Lonerism", shows: 1, songs: 12 },
  { name: "InnerSpeaker", shows: 1, songs: 11 },
  { name: "B-Stage DJ Set", shows: 1, songs: 3 },
]

export const guests: Guest[] = [
  { guest: "JENNIE", song: "Dracula", city: "Boston", date: "2026-07-29" },
  { guest: "Djo", song: "Loser", city: "Boston", date: "2026-07-28" },
  { guest: "Dua Lipa", song: "Afterthought", city: "London", date: "2026-05-07" },
  { guest: "Dua Lipa", song: "Houdini", city: "London", date: "2026-05-07" },
  { guest: "Justice", song: "Neverender", city: "Paris", date: "2026-05-03" },
  { guest: "A$AP Rocky", song: "Sundress", city: "Biddinghuizen", date: "2019-08-18" },
  { guest: "A$AP Rocky", song: "L$D", city: "Biddinghuizen", date: "2019-08-18" },
  { guest: "A$AP Rocky", song: "Sundress", city: "Indio", date: "2019-04-20" },
  { guest: "A$AP Rocky", song: "L$D", city: "Indio", date: "2019-04-20" },
  { guest: "Wayne Coyne", song: "Are You a Hypnotist??", city: "Santa Barbara", date: "2013-11-01" },
  { guest: "Sean Ono Lennon", song: "Desire Be Desire Go", city: "Columbia", date: "2013-10-04" },
  { guest: "Craig Nicholls", song: "Get Free", city: "Sydney", date: "2010-05-15" },
]

export const flags: NoteFlag[] = [
  { key: "intro_outro", label: "An intro or an outro", count: 120 },
  { key: "jam", label: "Jammed or extended", count: 87 },
  { key: "debut", label: "First time ever played", count: 70 },
  { key: "snippet", label: "Carried a snippet of another song", count: 48 },
  { key: "guest_mentioned", label: "Someone else on stage", count: 46 },
  { key: "reprise", label: "A reprise", count: 39 },
  { key: "tour_debut", label: "First time on that tour", count: 36 },
  { key: "instrumental", label: "Played instrumental", count: 36 },
  { key: "long_awaited_return", label: "Back after years away", count: 22 },
  { key: "partial", label: "Cut short or played in part", count: 20 },
  { key: "fan_request", label: "Asked for from the floor", count: 9 },
  { key: "solo", label: "A solo", count: 8 },
  { key: "dedication", label: "Dedicated to someone", count: 7 },
]

export const teases: Tease[] = [
  { title: "Sestri Levante", count: 32 },
  { title: "The Bold Arrow of Time", count: 4 },
  { title: "Mind Melt", count: 2 },
  { title: "Half Full Glass of Wine", count: 1 },
  { title: "Jolene", count: 1 },
  { title: "War Pigs", count: 1 },
]

export const debutCheck = {
  claims: 70,
  confirmed: 60,
  contradicted: 10,
  contradictions: [
    { song: "Sun's Coming Up", claimedOn: "2022-10-01", earliest: "2010-12-15", yearsEarlier: 11.8 },
    { song: "Mind Mischief", claimedOn: "2021-09-07", earliest: "2012-10-15", yearsEarlier: 8.9 },
    { song: "Gossip", claimedOn: "2021-03-05", earliest: "2019-04-11", yearsEarlier: 1.9 },
    { song: "Why Won't They Talk to Me?", claimedOn: "2013-10-02", earliest: "2013-02-22", yearsEarlier: 0.6 },
  ],
}

export const notesTotal = 536
