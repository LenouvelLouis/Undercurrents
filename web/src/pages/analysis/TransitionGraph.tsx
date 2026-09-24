import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import SongSelect from "../../components/SongSelect";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Song, Transitions } from "../../lib/types";

const GRAPH_TOP_N = 6;

export default function TransitionGraph() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [selected, setSelected] = useState<Song | null>(null);
  const [transitions, setTransitions] = useState<Transitions | null>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  useEffect(() => {
    api
      .songs()
      .then((data) => {
        setSongs(data);
        const elephant = data.find((s) => s.name === "Elephant");
        setSelected(elephant ?? data[0] ?? null);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selected) {
      api.transitions(selected.id).then(setTransitions).catch(() => {});
    }
  }, [selected]);

  const topFollowOns = transitions?.follow_ons.slice(0, GRAPH_TOP_N) ?? [];
  const maxP = Math.max(...(transitions?.follow_ons.map((f) => f.probability) ?? []), 0.0001);

  // Canvas and node layout, both derived from how many follow-ons are actually being
  // drawn: a source with only 2-3 real follow-ons gets a compact graph instead of huge
  // gaps, and one with many spreads targets across the full card height instead of
  // cramming into a fixed 4-slot layout.
  const width = 560;
  const height = 480;
  const sourceX = 80;
  const sourceY = height - 90;
  const topMargin = 34;
  const bottomMargin = 80;
  const spread = height - topMargin - bottomMargin;
  const targetX = 350;
  const targetY = (i: number) => (topFollowOns.length > 1 ? topMargin + (spread * i) / (topFollowOns.length - 1) : height / 2);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.silhouetteLasers.src} alt={PHOTOS.silhouetteLasers.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Transition Graph
          </h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          What follows a given song
          <br />
          line weight &amp; arrow size = transition probability
        </p>
      </div>
      <div className="mt-10 grid grid-cols-5 gap-6">
        <Card className="anim-fade-in-up relative col-span-5 flex items-center justify-center overflow-hidden lg:col-span-3" tinted accent="ember">
          <div className="pointer-events-none absolute -bottom-16 -right-10 h-56 w-56 rounded-full bg-ember/15 blur-3xl" />
          <svg viewBox={`0 0 ${width} ${height}`} className="relative w-full">
            <defs>
              <filter id="source-glow" x="-150%" y="-150%" width="400%" height="400%">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              {topFollowOns.map((follow, i) => (
                <marker
                  key={follow.song_id}
                  id={`arrow-${i}`}
                  viewBox="0 0 10 10"
                  refX="8"
                  refY="5"
                  markerWidth={4 + (follow.probability / maxP) * 3}
                  markerHeight={4 + (follow.probability / maxP) * 3}
                  orient="auto-start-reverse"
                >
                  <path d="M 0 0 L 10 5 L 0 10 z" fill="#ff9270" />
                </marker>
              ))}
            </defs>

            {/* faint radial guide rings so the source node reads as the graph's origin */}
            {[70, 130, 190].map((r) => (
              <circle key={r} cx={sourceX} cy={sourceY} r={r} fill="none" stroke="rgba(255,255,255,0.04)" />
            ))}

            {topFollowOns.map((follow, i) => {
              const ty = targetY(i);
              const c1x = sourceX + (targetX - sourceX) * 0.55;
              const c1y = sourceY;
              const c2x = sourceX + (targetX - sourceX) * 0.45;
              const c2y = ty;
              const isHovered = hoveredId === follow.song_id;
              const strokeW = (1.5 + (follow.probability / maxP) * 6) * (isHovered ? 1.4 : 1);
              return (
                <g
                  key={follow.song_id}
                  className="anim-fade-in-up cursor-pointer"
                  style={{ animationDelay: `${0.3 + i * 0.1}s` }}
                  onMouseEnter={() => setHoveredId(follow.song_id)}
                  onMouseLeave={() => setHoveredId((h) => (h === follow.song_id ? null : h))}
                >
                  <path
                    d={`M ${sourceX} ${sourceY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${targetX - 12} ${ty}`}
                    fill="none"
                    stroke={isHovered ? "#ff9270" : "#e2492f"}
                    strokeWidth={strokeW}
                    opacity={isHovered ? 0.95 : 0.6}
                    strokeLinecap="round"
                    markerEnd={`url(#arrow-${i})`}
                    className="anim-draw-in transition-all duration-150"
                    style={{ animationDelay: `${0.1 + i * 0.1}s` }}
                  />
                  <circle
                    cx={targetX}
                    cy={ty}
                    r={(5 + (follow.probability / maxP) * 4) * (isHovered ? 1.25 : 1)}
                    fill="#ff9270"
                    className="anim-pop-in transition-all duration-150"
                    style={{ animationDelay: `${0.7 + i * 0.1}s` }}
                  />
                  <text
                    x={targetX + 14}
                    y={ty + 4}
                    className="font-mono"
                    fontSize="12"
                    fontWeight={600}
                    fill={isHovered ? "#ffd0c0" : "white"}
                  >
                    {follow.song_name}
                  </text>
                  <text x={targetX + 14} y={ty + 18} className="font-mono" fontSize="9" fill="rgba(255,255,255,0.4)">
                    {Math.round(follow.probability * 100)}% of the time
                  </text>
                </g>
              );
            })}
            <circle cx={sourceX} cy={sourceY} r={13} fill="#e2492f" filter="url(#source-glow)" className="anim-pop-in" />
            <text x={sourceX} y={sourceY + 34} textAnchor="middle" className="font-mono" fontSize="12" fontWeight={700} fill="white">
              {selected?.name}
            </text>
            <text x={sourceX} y={sourceY + 48} textAnchor="middle" className="font-mono" fontSize="9" fill="rgba(255,255,255,0.4)">
              SOURCE SONG
            </text>
          </svg>
        </Card>
        <Card className="anim-fade-in-up col-span-5 lg:col-span-2" style={{ animationDelay: "0.1s" }}>
          <SongSelect songs={songs} value={selected} onChange={setSelected} accent="ember" />
          <div className="mt-5 flex items-center justify-between">
            <span className="text-[13px] font-medium text-white/55">Ranked follow-ons</span>
            {(transitions?.follow_ons.length ?? 0) > GRAPH_TOP_N && (
              <span className="font-mono text-[10px] text-white/30">top {GRAPH_TOP_N} drawn on the graph</span>
            )}
          </div>
          <div className="mt-3 max-h-[520px] space-y-3 overflow-y-auto pr-1">
            {transitions?.follow_ons.map((follow, i) => {
              const isHovered = hoveredId === follow.song_id;
              const isDrawn = i < GRAPH_TOP_N;
              return (
                <div
                  key={follow.song_id}
                  className={`anim-fade-in-up flex items-center gap-3 rounded-md px-1.5 py-1 transition-colors ${
                    isHovered ? "bg-ember/10" : ""
                  } ${isDrawn ? "cursor-pointer" : ""}`}
                  style={{ animationDelay: `${i * 0.05}s` }}
                  onMouseEnter={() => isDrawn && setHoveredId(follow.song_id)}
                  onMouseLeave={() => setHoveredId((h) => (h === follow.song_id ? null : h))}
                >
                  <span className="w-5 shrink-0 font-mono text-[11px] text-white/30">{String(i + 1).padStart(2, "0")}</span>
                  <span
                    className={`min-w-0 shrink grow-[12] basis-0 truncate font-display text-sm font-medium ${isHovered ? "text-ember-light" : ""}`}
                  >
                    {follow.song_name}
                  </span>
                  <div className="h-1.5 min-w-0 shrink grow-[16] basis-0 overflow-hidden rounded-full bg-white/5">
                    <div
                      className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                      style={{ width: `${Math.max(4, (follow.probability / maxP) * 100)}%`, animationDelay: `${0.15 + i * 0.05}s` }}
                    />
                  </div>
                  <span className="w-9 shrink-0 text-right font-mono text-xs text-white/50">{Math.round(follow.probability * 100)}%</span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.guitaristClose}
          accent="ember"
          className="col-span-3 h-[19rem] lg:col-span-1"
          focus="center 25%"
        />
        <PhotoPanel
          photo={PHOTOS.silhouetteLasers}
          accent="ember"
          tag="song into song"
          className="col-span-3 h-[19rem] lg:col-span-2"
          focus="center 50%"
          style={{ animationDelay: "0.08s" }}
        />
      </div>
    </div>
  );
}
