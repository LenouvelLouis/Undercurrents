import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { AudioFeatures, WeatherReport } from "../../lib/types";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

// The tempo of the set drawn against position. A line, not bars: position is a continuous
// axis and the question is the shape of the curve, not the value at any one slot.
function TempoArc({ points }: { points: { position: number; avg_bpm: number; samples: number }[] }) {
  if (points.length < 2) return null;
  const width = 620;
  const height = 210;
  const pad = { left: 44, right: 14, top: 16, bottom: 30 };
  const bpms = points.map((p) => p.avg_bpm);
  const min = Math.floor((Math.min(...bpms) - 4) / 5) * 5;
  const max = Math.ceil((Math.max(...bpms) + 4) / 5) * 5;
  const x = (position: number) =>
    pad.left + ((position - points[0].position) / (points[points.length - 1].position - points[0].position)) *
      (width - pad.left - pad.right);
  const y = (bpm: number) =>
    pad.top + (1 - (bpm - min) / (max - min)) * (height - pad.top - pad.bottom);

  const path = points.map((p, i) => `${i ? "L" : "M"}${x(p.position).toFixed(1)},${y(p.avg_bpm).toFixed(1)}`).join(" ");
  const ticks = [min, (min + max) / 2, max];

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Average tempo by position in the set">
      {ticks.map((tick) => (
        <g key={tick}>
          <line x1={pad.left} x2={width - pad.right} y1={y(tick)} y2={y(tick)} stroke="rgba(255,255,255,0.07)" />
          <text x={pad.left - 8} y={y(tick) + 3} textAnchor="end" fontSize="9" fill="rgba(255,255,255,0.35)" className="font-mono">
            {tick}
          </text>
        </g>
      ))}
      <path d={path} fill="none" stroke="#a531d6" strokeWidth={2} strokeLinejoin="round" />
      {points.map((p) => (
        <circle key={p.position} cx={x(p.position)} cy={y(p.avg_bpm)} r={2.6} fill="#e2a6ff">
          <title>{`Position ${p.position}: ${p.avg_bpm} bpm across ${p.samples} performances`}</title>
        </circle>
      ))}
      {points.filter((_, i) => i % 4 === 0).map((p) => (
        <text key={p.position} x={x(p.position)} y={height - 10} textAnchor="middle" fontSize="9" fill="rgba(255,255,255,0.35)" className="font-mono">
          {p.position}
        </text>
      ))}
      <text x={pad.left} y={height - 10} fontSize="9" fill="rgba(255,255,255,0.25)" className="font-mono">
        position in the set
      </text>
    </svg>
  );
}

export default function AudioProfile() {
  const [audio, setAudio] = useState<AudioFeatures | null>(null);
  const [weather, setWeather] = useState<WeatherReport | null>(null);

  useEffect(() => {
    api.audioFeatures().then(setAudio).catch(() => {});
    api.weather().then(setWeather).catch(() => {});
  }, []);

  if (!audio) return <div className="font-mono text-sm text-white/40">Loading...</div>;

  const slowest = audio.songs.slice(0, 6);
  const fastest = [...audio.songs].reverse().slice(0, 6);
  const maxKey = Math.max(...audio.keys.map((k) => k.songs), 1);
  const wet = weather?.outdoor_wet_vs_dry.find((r) => r.condition === "wet");
  const dry = weather?.outdoor_wet_vs_dry.find((r) => r.condition === "dry");

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.synthTable.src} alt={PHOTOS.synthTable.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Sound Profile
          </h1>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-white/50 sm:text-right">
          Tempo, key and loudness per song
          <br />
          {percent(audio.coverage.performance_coverage)} of performances covered
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-y-6 xl:grid-cols-[1.25fr_1fr] gap-6">
        <Card className="anim-fade-in-up" tinted accent="violet">
          <p className="text-[13px] font-medium text-white/55">
            The tempo of a night
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-white/45">
            Average tempo at each slot in the running order, across every performance where
            the song has a measured tempo. Only positions with at least twenty samples are
            drawn, which is why the line stops before the encore thins out.
          </p>
          <div className="mt-5">
            <TempoArc points={audio.tempo_arc} />
          </div>
        </Card>

        <Card className="anim-fade-in-up" style={{ animationDelay: "0.05s" }}>
          <p className="text-[13px] font-medium text-white/55">
            How much is actually measured
          </p>
          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <p className="font-display text-4xl font-bold text-cream">
                {percent(audio.coverage.performance_coverage)}
              </p>
              <p className="text-[13px] font-medium mt-1 text-white/50">
                of performances
              </p>
            </div>
            <div>
              <p className="font-display text-4xl font-bold text-white/45">
                {percent(audio.coverage.song_coverage)}
              </p>
              <p className="text-[13px] font-medium mt-1 text-white/50">
                of the catalogue
              </p>
            </div>
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-white/45">
            The two differ because what is missing is mostly what is rarely played:{" "}
            {audio.coverage.songs_total - audio.coverage.songs_with_audio} songs without a
            measurement account for only{" "}
            {percent(1 - audio.coverage.performance_coverage)} of nights on stage. The source
            stopped accepting new analyses in 2022, so nothing from the 2025 record will ever
            appear here.
          </p>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card className="anim-fade-in-up" style={{ animationDelay: "0.1s" }}>
          <p className="text-[13px] font-medium text-white/55">Slowest</p>
          <div className="mt-4 space-y-2">
            {slowest.map((song) => (
              <div key={song.song_name} className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 truncate text-sm text-white/65">{song.song_name}</span>
                <span className="shrink-0 font-mono text-[11px] text-white/45">
                  {Math.round(song.bpm)}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="anim-fade-in-up" style={{ animationDelay: "0.15s" }}>
          <p className="text-[13px] font-medium text-white/55">Fastest</p>
          <div className="mt-4 space-y-2">
            {fastest.map((song) => (
              <div key={song.song_name} className="flex items-baseline justify-between gap-3">
                <span className="min-w-0 truncate text-sm text-white/65">{song.song_name}</span>
                <span className="shrink-0 font-mono text-[11px] text-white/45">
                  {Math.round(song.bpm)}
                </span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="anim-fade-in-up" style={{ animationDelay: "0.2s" }}>
          <p className="text-[13px] font-medium text-white/55">
            Keys they write in
          </p>
          <div className="mt-4 space-y-2">
            {audio.keys.slice(0, 6).map((key) => (
              <div key={key.key} className="flex items-center gap-3">
                <span className="w-16 shrink-0 font-mono text-[11px] text-white/55">{key.key}</span>
                <div className="h-2 grow overflow-hidden rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                    style={{ width: `${(key.songs / maxKey) * 100}%` }}
                  />
                </div>
                <span className="w-6 shrink-0 text-right font-mono text-[11px] text-white/40">
                  {key.songs}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {weather && (
        <Card className="anim-fade-in-up mt-6" style={{ animationDelay: "0.25s" }}>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-[13px] font-medium text-white/55">
              Does the rain shorten an outdoor show?
            </p>
            <p className="text-[13px] italic text-white/35">
              {weather.shows_with_weather} of {weather.shows_total} shows have weather on file
            </p>
          </div>
          {wet && dry ? (
            <>
              <div className="mt-4 flex flex-wrap items-baseline gap-8">
                <div>
                  <p className="font-display text-4xl font-bold text-cream">{dry.avg_songs}</p>
                  <p className="text-[13px] font-medium mt-1 text-white/50">
                    songs, dry night ({dry.shows} shows)
                  </p>
                </div>
                <div>
                  <p className="font-display text-4xl font-bold text-cream">{wet.avg_songs}</p>
                  <p className="text-[13px] font-medium mt-1 text-white/50">
                    songs, wet night ({wet.shows} shows)
                  </p>
                </div>
              </div>
              <p className="mt-4 text-[13px] leading-relaxed text-white/45">
                No difference worth reporting, and with {wet.shows} wet shows there is not
                enough here to find one even if it existed. It is on the page because the
                question is a reasonable one to ask and the answer, so far, is no.
              </p>
            </>
          ) : (
            <p className="mt-3 font-mono text-[11px] text-white/45">
              Not enough outdoor shows have weather on file yet to make the comparison.
            </p>
          )}
          <p className="mt-3 text-[13px] leading-relaxed text-white/35">{weather.caveat}</p>
        </Card>
      )}

      <PhotoPanel
        photo={PHOTOS.roundStageOverhead}
        accent="violet"
        tag="measured, where measurable"
        className="mt-6 h-64"
        focus="center 40%"
        style={{ animationDelay: "0.3s" }}
      />
    </div>
  );
}
