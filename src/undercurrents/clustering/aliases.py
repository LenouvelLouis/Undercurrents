"""Hand-curated corrections for song titles that MusicBrainz's automated search either
can't resolve or resolves incorrectly. Populated from inspecting the real
`data/undercurrents.db` at the end of Phase 0 (see the Phase 1 design spec's Context
section for how each entry was found).

Three categories, applied in this order by `title_resolution.py`:
- EXCLUDE: not a real song (intro, jam/improvisation segment, blank entry) — dropped from
  clustering entirely rather than merged anywhere.
- MERGE: a spelling variant of another song that already exists as its own row — merged
  into that row via `songs.canonical_song_id`, no MusicBrainz call needed.
- FIX_TEXT: a standalone text correction (no duplicate row to merge into) — the song's own
  `name` is corrected in place, then MusicBrainz is still queried under the corrected name.
"""

EXCLUDE: frozenset[str] = frozenset(
    {
        "",
        "Intro",
        "Intro (Walk On)",
        "Rushium Intro",
        "Aionwell Lab Intro",
        "Aionwell Lab Video One",
        "Auto-Prog III",
        "Auto-Prog No. 5",
        "Auto-Prog mk. II",
        "Jam",
        "The Jam Song",
        "Deadbeat Jam",
        "improvisation",
    }
)

MERGE: dict[str, str] = {
    "Halcyon And On And On": "Halcyon + On + On",
}

FIX_TEXT: dict[str, str] = {
    "She Just Won’t Believe Me": "She Just Won't Believe Me",
    "Tomorrow’s Dust": "Tomorrow's Dust",
}
