import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Song, SongRole as SongRoleData } from "../../lib/types";

const STAGE_ORDER: { key: keyof SongRoleData["probabilities"]; label: string }[] = [
  { key: "opener", label: "Opener" },
  { key: "mid", label: "Mid-set" },
  { key: "closer", label: "Closer" },
  { key: "encore", label: "Encore" },
];

// Same four categories as STAGE_ORDER, colored distinctly for the stacked comparison bar
// below (opener/mid/closer/encore are mutually exclusive per appearance, so their real
// probabilities already sum to ~1 and a 100%-wide stack is an honest read, not a rescale).
const STAGE_COLOR: Record<keyof SongRoleData["probabilities"], string> = {
  opener: "#e2a6ff",
  mid: "#a531d6",
  closer: "#d99a3f",
  encore: "#e2492f",
};

export default function SongRole() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Song | null>(null);
  const [role, setRole] = useState<SongRoleData | null>(null);
  const [compare, setCompare] = useState<SongRoleData[]>([]);

  useEffect(() => {
    api.songs().then(setSongs).catch(() => {});
  }, []);

  useEffect(() => {
    if (selected) {
      api.songRole(selected.id).then(setRole).catch(() => {});
    }
  }, [selected]);

  // Real per-song role breakdowns for the songs the model currently ranks most likely to
  // open the next show, fetched from the same /predictions/song-role endpoint the single-
  // song search above uses, just called once per ranked song instead of once on demand.
  useEffect(() => {
    api
      .nextSetlist()
      .then(async (predictions) => {
        const top = predictions.slice(0, 6);
        const roles = await Promise.all(
          top.map((p) =>
            api
              .songRole(p.song_id)
              .catch(() => null),
          ),
        );
        setCompare(roles.filter((r): r is SongRoleData => r !== null));
      })
      .catch(() => {});
  }, []);

  const matches = query.length > 0 ? songs.filter((s) => s.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8) : [];

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.guitaristClose.src} alt={PHOTOS.guitaristClose.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Song Role</h1>
        </div>
        <p className="max-w-xs text-sm leading-relaxed text-white/50 sm:text-right">
          Where in the set does a given song tend to land?
        </p>
      </div>

      <div className="mt-10 grid grid-cols-6 gap-6">
        <Card className="anim-fade-in-up col-span-6 lg:col-span-2">
          <div className="relative">
            <input
              value={selected ? selected.name : query}
              onChange={(e) => {
                setSelected(null);
                setRole(null);
                setQuery(e.target.value);
              }}
              placeholder="Search a song…"
              className="w-full rounded-full border border-white/20 bg-white/5 px-5 py-3 text-center text-white outline-none focus:border-violet"
            />
            {matches.length > 0 && !selected && (
              <ul className="absolute z-10 mt-2 w-full rounded-lg border border-white/10 bg-bg text-left shadow-xl">
                {matches.map((song) => (
                  <li
                    key={song.id}
                    className="cursor-pointer px-4 py-2 hover:bg-white/10"
                    onClick={() => {
                      setSelected(song);
                      setQuery("");
                    }}
                  >
                    {song.name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {!role && (
            <div className="mt-14 flex flex-col items-center gap-4 text-center text-white/30">
              <div className="h-24 w-24 rounded-full border-2 border-dashed border-white/20" />
              <p className="font-mono text-xs">Pick a song to see its role distribution</p>
            </div>
          )}

          {role && (
            <div className="anim-fade-in-up mt-8">
              <h2 className="text-center font-display text-xl font-bold">{role.song_name}</h2>

              {/* Horizontal stage-position timeline (dot size and glow scale with probability) */}
              <div className="relative mx-2 mt-10 mb-2">
                <div className="absolute left-0 right-0 top-4 h-px bg-white/10" />
                <div className="flex items-start justify-between">
                  {STAGE_ORDER.map(({ key, label }, i) => {
                    const p = role.probabilities[key];
                    const size = 14 + p * 36;
                    return (
                      <div key={key} className="flex w-1/4 flex-col items-center">
                        <span className="mb-1 font-mono text-[11px] text-white/50">{Math.round(p * 100)}%</span>
                        <div
                          className="anim-pop-in rounded-full bg-gradient-to-br from-violet-light to-violet shadow-glow-violet"
                          style={{ width: size, height: size, animationDelay: `${0.1 + i * 0.1}s` }}
                        />
                        <span className="text-[13px] font-medium mt-3 text-white/55">{label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="mt-8 space-y-3">
                {STAGE_ORDER.map(({ key, label }, i) => (
                  <div key={key} className="anim-fade-in-up" style={{ animationDelay: `${0.3 + i * 0.08}s` }}>
                    <div className="flex justify-between font-mono text-xs text-white/50">
                      <span>{label}</span>
                      <span>{Math.round(role.probabilities[key] * 100)}%</span>
                    </div>
                    <ProgressBar percentage={role.probabilities[key] * 100} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="anim-fade-in-up col-span-6 lg:col-span-3" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-medium text-white/55">Across the next predicted setlist</span>
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              {STAGE_ORDER.map(({ key, label }) => (
                <span key={key} className="flex items-center gap-1.5 font-mono text-[10px] text-white/40">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: STAGE_COLOR[key] }} />
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-6 space-y-5">
            {compare.map((entry, i) => (
              <div key={entry.song_id} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.06}s` }}>
                <div className="mb-1.5 flex items-center justify-between font-mono text-xs text-white/60">
                  <span className="truncate font-display text-sm font-medium text-white">{entry.song_name}</span>
                </div>
                <div className="flex h-6 w-full overflow-hidden rounded-md bg-white/5">
                  {STAGE_ORDER.map(({ key }) => {
                    const p = entry.probabilities[key];
                    if (p <= 0) return null;
                    return (
                      <div
                        key={key}
                        className="anim-width-in flex items-center justify-center transition-opacity hover:opacity-80"
                        style={{ width: `${p * 100}%`, backgroundColor: STAGE_COLOR[key] }}
                        title={`${key}: ${Math.round(p * 100)}%`}
                      >
                        {p >= 0.14 && (
                          <span className="font-mono text-[9px] font-bold text-ink/80">{Math.round(p * 100)}%</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            {compare.length === 0 && (
              <p className="font-mono text-xs text-white/30">Loading the current top predictions…</p>
            )}
          </div>
        </Card>

        {/* A tall frame closes the row, so the two data cards are read against the show
            they describe rather than in isolation. */}
        <PhotoPanel
          photo={PHOTOS.guitaristClose}
          accent="violet"
          tag="mid-set"
          className="col-span-6 h-[16rem] lg:col-span-1 lg:h-auto"
          focus="center 30%"
          style={{ animationDelay: "0.15s" }}
        />

        <PhotoPanel
          photo={PHOTOS.backyardPortrait}
          accent="violet"
          tag="between tours"
          className="col-span-6 h-[20rem] lg:col-span-2"
          focus="center 20%"
          style={{ animationDelay: "0.3s" }}
        />
        <PhotoPanel
          photo={PHOTOS.artistRedSeats}
          accent="violet"
          className="col-span-6 h-[20rem] lg:col-span-4"
          focus="center 40%"
          style={{ animationDelay: "0.36s" }}
        />
      </div>
    </div>
  );
}
