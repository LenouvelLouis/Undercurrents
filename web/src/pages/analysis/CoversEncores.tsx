import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { CoverArtist, Encores } from "../../lib/types";

function formatShort(iso: string | null) {
  if (!iso) return "unknown";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

export default function CoversEncores() {
  const [covers, setCovers] = useState<CoverArtist[]>([]);
  const [encores, setEncores] = useState<Encores | null>(null);
  const [openArtist, setOpenArtist] = useState<string | null>(null);

  useEffect(() => {
    api.covers().then(setCovers).catch(() => {});
    api.encores().then(setEncores).catch(() => {});
  }, []);

  const totalCovers = covers.reduce((sum, c) => sum + c.play_count, 0);
  const maxCover = Math.max(...covers.map((c) => c.play_count), 1);
  const topEncores = encores?.songs.slice(0, 12) ?? [];
  const maxEncore = Math.max(...topEncores.map((s) => s.encore_count), 1);

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.guitaristClose.src} alt={PHOTOS.guitaristClose.alt} size={56} accent="ember" />
          <h1 className="font-display text-6xl font-bold">
            Covers &amp;
            <br />
            Encores
          </h1>
        </div>
        <p className="text-right font-mono text-xs italic text-white/40">
          {totalCovers} cover performances from {covers.length} artists
          <br />
          {encores ? `${encores.encore_entries} encore slots across ${encores.shows_with_encore} shows` : ""}
        </p>
      </div>

      <div className="mt-10 grid grid-cols-6 gap-6">
        {/* Encore headline: how often a show even has one, straight from the counts. */}
        <Card tinted accent="ember" className="anim-fade-in-up col-span-6 flex flex-col justify-center py-10 text-center md:col-span-3 lg:col-span-2">
          <div className="font-mono text-xs uppercase tracking-widest text-white/50">Shows with an encore</div>
          <div className="mt-3 font-display text-7xl font-bold leading-none">
            {encores?.encore_rate != null ? `${Math.round(encores.encore_rate * 100)}%` : "N/A"}
          </div>
          <div className="mt-3 font-mono text-xs text-white/50">
            {encores ? `${encores.shows_with_encore} of ${encores.shows_total} logged concerts` : ""}
          </div>
        </Card>

        <Card className="anim-fade-in-up col-span-6 md:col-span-3 lg:col-span-4" style={{ animationDelay: "0.05s" }}>
          <div className="font-mono text-sm uppercase tracking-widest text-white/40">
            What closes the show
          </div>
          <div className="mt-5 space-y-3">
            {topEncores.map((song, i) => (
              <div key={song.song_id} className="flex items-center gap-3">
                <span className="w-6 shrink-0 font-mono text-xs text-white/30">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="min-w-0 shrink grow-[12] basis-0 truncate font-display text-sm font-medium">
                  {song.song_name}
                </span>
                <div className="h-2 min-w-0 shrink grow-[16] basis-0 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${(song.encore_count / maxEncore) * 100}%`, animationDelay: `${0.1 + i * 0.04}s` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right font-mono text-xs text-white/50">
                  {song.encore_count}
                </span>
              </div>
            ))}
            {topEncores.length === 0 && <p className="font-mono text-xs text-white/30">Loading encores…</p>}
          </div>
        </Card>

        <PhotoPanel
          photo={PHOTOS.singerConfetti}
          accent="ember"
          tag="the last song"
          className="col-span-6 h-[17rem] lg:col-span-4"
          focus="center 45%"
          style={{ animationDelay: "0.15s" }}
        />
        <PhotoPanel
          photo={PHOTOS.guitaristClose}
          accent="ember"
          className="col-span-6 h-[17rem] lg:col-span-2"
          focus="center 28%"
          style={{ animationDelay: "0.2s" }}
        />

        {/* Covers, ranked by how many times the band played that artist's song. Clicking an
            artist reveals which songs, which is the part the counts alone never tell you. */}
        <Card className="anim-fade-in-up col-span-6" style={{ animationDelay: "0.25s" }}>
          <div className="flex items-baseline justify-between">
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Artists covered, most played first
            </div>
            <div className="font-mono text-[10px] text-white/30">click an artist for the songs</div>
          </div>
          <div className="mt-5 grid grid-cols-1 gap-x-8 gap-y-3 lg:grid-cols-2">
            {covers.map((artist, i) => {
              const open = openArtist === artist.artist_id;
              return (
                <div key={artist.artist_id} className="anim-fade-in-up" style={{ animationDelay: `${Math.min(i, 20) * 0.03}s` }}>
                  <button
                    type="button"
                    onClick={() => setOpenArtist((a) => (a === artist.artist_id ? null : artist.artist_id))}
                    className="flex w-full items-center gap-3 text-left"
                  >
                    <span className="min-w-0 shrink grow-[12] basis-0 truncate font-display text-sm font-medium text-white">
                      {artist.artist_name}
                    </span>
                    <div className="h-1.5 min-w-0 shrink grow-[14] basis-0 overflow-hidden rounded-full bg-white/5">
                      <div
                        className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                        style={{ width: `${(artist.play_count / maxCover) * 100}%`, animationDelay: `${0.1 + Math.min(i, 20) * 0.03}s` }}
                      />
                    </div>
                    <span className="w-16 shrink-0 text-right font-mono text-xs text-white/50">
                      {artist.play_count}x
                    </span>
                  </button>
                  {open && (
                    <div className="anim-fade-in-up mt-2 rounded-lg border border-white/10 bg-white/[0.02] p-3">
                      <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">
                        {formatShort(artist.first_played)} to {formatShort(artist.last_played)} ·{" "}
                        {artist.song_count} song{artist.song_count === 1 ? "" : "s"}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {artist.songs.map((song) => (
                          <span
                            key={song.song_name}
                            className="rounded-full border border-ember/40 bg-ember/10 px-2.5 py-1 font-mono text-[10px] text-ember-light"
                          >
                            {song.song_name}
                            <span className="ml-1.5 text-white/40">{song.play_count}x</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
            {covers.length === 0 && <p className="font-mono text-xs text-white/30">Loading covers…</p>}
          </div>
        </Card>
      </div>
    </div>
  );
}
