import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { DebutCheck, NightNotes as NightNotesData } from "../../lib/types";

const FLAG_LABELS: Record<string, string> = {
  intro_outro: "an intro or an outro",
  jam: "jammed or extended",
  debut: "first time ever played",
  snippet: "carried a snippet of something else",
  guest_mentioned: "someone else on stage",
  reprise: "a reprise",
  tour_debut: "first time on that tour",
  instrumental: "played instrumental",
  long_awaited_return: "back after years away",
  partial: "cut short or played in part",
  fan_request: "asked for from the floor",
  solo: "a solo",
  dedication: "dedicated to someone",
};

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function NightNotes() {
  const [data, setData] = useState<NightNotesData | null>(null);
  const [debuts, setDebuts] = useState<DebutCheck | null>(null);

  useEffect(() => {
    api.nightNotes().then(setData).catch(() => {});
    api.debutCheck().then(setDebuts).catch(() => {});
  }, []);

  if (!data) return <div className="font-mono text-sm text-white/40">Loading...</div>;

  const maxFlag = Math.max(...data.flags.map((f) => f.count), 1);
  const maxFormat = Math.max(...data.formats.map((f) => f.shows), 1);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerBlur.src} alt={PHOTOS.singerBlur.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Night Notes
          </h1>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-white/50 sm:text-right">
          What happened on the night, not which songs were played
          <br />
          {data.notes_total} margin notes, {data.guests.length} guest appearances
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-y-6 xl:grid-cols-[1fr_1fr] gap-6">
        <Card className="anim-fade-in-up" tinted accent="ember">
          <p className="text-[13px] font-medium text-white/55">
            How the show was shaped
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-white/45">
            Named segments, counted by the shows that had one. A B-Stage is a satellite
            platform out in the crowd; an album title means the record was played end to end.
          </p>
          <div className="mt-5 space-y-3">
            {data.formats.map((format, i) => (
              <div key={format.name} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 truncate text-sm text-cream">{format.name}</span>
                  <span className="shrink-0 font-mono text-[11px] text-white/45">
                    {format.shows} {format.shows === 1 ? "show" : "shows"} · {format.songs} songs
                  </span>
                </div>
                <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${(format.shows / maxFormat) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="anim-fade-in-up" style={{ animationDelay: "0.05s" }}>
          <p className="text-[13px] font-medium text-white/55">
            Who else was on stage
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-white/45">
            Every credited guest in eighteen years. The source names them explicitly, so this
            list is complete rather than inferred from the margin notes.
          </p>
          <div className="mt-5 space-y-3">
            {data.guests.map((guest, i) => (
              <div
                key={`${guest.guest}-${guest.event_date}-${guest.song_name}`}
                className="anim-fade-in-up flex items-baseline justify-between gap-3 border-b border-white/[0.06] pb-2"
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-cream">{guest.guest}</p>
                  <p className="truncate font-mono text-[10px] text-white/35">
                    {guest.song_name}
                    {guest.city ? ` · ${guest.city}` : ""}
                  </p>
                </div>
                <span className="shrink-0 font-mono text-[10px] text-white/40">
                  {formatDate(guest.event_date)}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-y-6 xl:grid-cols-[1.2fr_1fr] gap-6">
        <Card className="anim-fade-in-up" style={{ animationDelay: "0.1s" }}>
          <p className="text-[13px] font-medium text-white/55">
            What the margin notes say
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-white/45">
            {data.notes_total} free-text notes, sorted into categories by pattern matching.
            Each match stores the phrase that triggered it, so a wrong one can be traced to
            its cause rather than taken on faith.
          </p>
          <div className="mt-5 space-y-2.5">
            {data.flags.map((flag) => (
              <div key={flag.flag} className="flex items-center gap-3">
                <span className="min-w-0 shrink grow-[10] basis-0 truncate text-sm text-white/65">
                  {FLAG_LABELS[flag.flag] ?? flag.flag}
                </span>
                <div className="h-2 min-w-0 shrink grow-[14] basis-0 overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${(flag.count / maxFlag) * 100}%` }}
                  />
                </div>
                <span className="w-8 shrink-0 text-right font-mono text-[11px] text-white/45">
                  {flag.count}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          {debuts && (
            <Card className="anim-fade-in-up" tinted accent="violet" style={{ animationDelay: "0.15s" }}>
              <p className="text-[13px] font-medium text-violet-light/70">
                Checking the debut claims
              </p>
              <div className="mt-4 flex items-baseline gap-6">
                <div>
                  <p className="font-display text-4xl font-bold text-cream">{debuts.confirmed}</p>
                  <p className="text-[13px] font-medium mt-1 text-white/50">
                    backed by the archive
                  </p>
                </div>
                <div>
                  <p className="font-display text-4xl font-bold text-white/45">
                    {debuts.contradicted}
                  </p>
                  <p className="text-[13px] font-medium mt-1 text-white/50">
                    contradicted
                  </p>
                </div>
              </div>
              <p className="mt-4 text-[13px] leading-relaxed text-white/45">
                A note saying "live debut" is a claim; the performance history is evidence.
                Where they disagree neither is assumed right, because the archive thins out
                before about 2010 and a missing show looks exactly like a wrong note.
              </p>
              {debuts.contradictions.length > 0 && (
                <div className="mt-4 space-y-1.5 border-t border-white/10 pt-3">
                  {debuts.contradictions.slice(0, 4).map((c) => (
                    <div
                      key={`${c.song_name}-${c.claimed_on}`}
                      className="flex items-baseline justify-between gap-3"
                    >
                      <span className="min-w-0 truncate font-mono text-[11px] text-white/55">
                        {c.song_name}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] text-white/35">
                        played {Math.round(c.days_earlier / 365)} yr earlier
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          )}

          <Card className="anim-fade-in-up" style={{ animationDelay: "0.2s" }}>
            <p className="text-[13px] font-medium text-white/55">
              Songs dropped inside other songs
            </p>
            <div className="mt-4 space-y-2">
              {data.teases.map((tease) => (
                <div key={tease.title} className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 truncate text-sm text-white/65">{tease.title}</span>
                  <span className="shrink-0 font-mono text-[11px] text-white/40">
                    {tease.count}x
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <PhotoPanel
        photo={PHOTOS.guitaristClose}
        accent="ember"
        tag="in the margin"
        className="mt-6 h-64"
        focus="center 35%"
        style={{ animationDelay: "0.25s" }}
      />
    </div>
  );
}
