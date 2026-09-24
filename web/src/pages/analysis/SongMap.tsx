import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { SongMapPoint } from "../../lib/types";

// One hue per cluster id, cycled. Cluster -1 is the clustering step's "no group" label,
// so it gets a deliberately neutral grey rather than a colour that implies a group.
const CLUSTER_HUES = ["#a531d6", "#e2492f", "#d99a3f", "#e2a6ff", "#ff9270", "#f0c581", "#9d6bff", "#ff6f9c"];
const NOISE_COLOR = "rgba(255,255,255,0.28)";

function colorFor(clusterId: number) {
  if (clusterId < 0) return NOISE_COLOR;
  return CLUSTER_HUES[clusterId % CLUSTER_HUES.length];
}

export default function SongMap() {
  const [points, setPoints] = useState<SongMapPoint[]>([]);
  const [hovered, setHovered] = useState<number | null>(null);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    api.songMap().then(setPoints).catch(() => {});
  }, []);

  const width = 760;
  const height = 520;
  const pad = 34;

  // Fitting the full bounding box to the SVG sounds right but is unreadable here: three
  // quarters of the songs sit inside an x span of about 2.6 while a handful of outliers
  // reach 14, so a plain min/max fit crushes the bulk of the map into one corner. The view
  // is framed on the 2nd-98th percentile instead, which keeps distances inside the frame
  // exactly proportional, and the few songs outside it are drawn on the edge as hollow
  // markers and counted underneath rather than silently dropped.
  const scale = useMemo(() => {
    if (points.length === 0) return null;
    const quantile = (sorted: number[], f: number) => sorted[Math.floor((sorted.length - 1) * f)];
    const xs = points.map((p) => p.x).sort((a, b) => a - b);
    const ys = points.map((p) => p.y).sort((a, b) => a - b);
    const minX = quantile(xs, 0.02);
    const maxX = quantile(xs, 0.98);
    const minY = quantile(ys, 0.02);
    const maxY = quantile(ys, 0.98);
    const spanX = maxX - minX || 1;
    const spanY = maxY - minY || 1;
    const clampTo = (lo: number, hi: number) => (v: number) => Math.min(hi, Math.max(lo, v));
    const clampX = clampTo(pad, width - pad);
    const clampY = clampTo(pad, height - pad);
    return {
      x: (v: number) => clampX(pad + ((v - minX) / spanX) * (width - pad * 2)),
      y: (v: number) => clampY(pad + ((v - minY) / spanY) * (height - pad * 2)),
      outside: (p: SongMapPoint) => p.x < minX || p.x > maxX || p.y < minY || p.y > maxY,
    };
  }, [points]);

  const outsideCount = useMemo(
    () => (scale ? points.filter((p) => scale.outside(p)).length : 0),
    [points, scale],
  );

  const maxPlays = Math.max(...points.map((p) => p.play_count), 1);

  // Which songs get a permanent label. The dense corner holds a dozen of the most-played
  // songs within a few pixels of each other, so "label anything popular" printed them all
  // on top of one another. Walk the songs most-played first and keep a label only where it
  // clears the ones already kept; everything else is still labelled on hover.
  const labelled = useMemo(() => {
    if (!scale) return new Set<number>();
    const kept: { x: number; y: number }[] = [];
    const ids = new Set<number>();
    for (const p of points.slice().sort((a, b) => b.play_count - a.play_count)) {
      if (kept.length >= 7) break;
      const x = scale.x(p.x);
      const y = scale.y(p.y);
      if (kept.every((k) => Math.hypot(k.x - x, k.y - y) > 96)) {
        kept.push({ x, y });
        ids.add(p.song_id);
      }
    }
    return ids;
  }, [points, scale]);

  const clusters = useMemo(() => {
    const map = new Map<number, { count: number; plays: number }>();
    for (const p of points) {
      const entry = map.get(p.cluster_id) ?? { count: 0, plays: 0 };
      entry.count += 1;
      entry.plays += p.play_count;
      map.set(p.cluster_id, entry);
    }
    return [...map.entries()]
      .map(([id, v]) => ({ id, ...v }))
      .sort((a, b) => b.count - a.count);
  }, [points]);

  const active = points.find((p) => p.song_id === (hovered ?? selected)) ?? null;
  const neighbours = useMemo(() => {
    if (!active) return [];
    return points
      .filter((p) => p.song_id !== active.song_id)
      .map((p) => ({ p, d: Math.hypot(p.x - active.x, p.y - active.y) }))
      .sort((a, b) => a.d - b.d)
      .slice(0, 6)
      .map((entry) => entry.p);
  }, [active, points]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.synthTable.src} alt={PHOTOS.synthTable.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Song Map
          </h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          {points.length} songs placed by how they co-occur in setlists
          <br />
          dot size = times played · colour = cluster
        </p>
      </div>

      <div className="mt-10 grid grid-cols-5 gap-6">
        <Card className="anim-fade-in-up col-span-5 lg:col-span-3">
          <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1">
            {clusters.map((c) => (
              <span key={c.id} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorFor(c.id) }} />
                <span className="text-[13px] font-medium text-white/55">
                  {c.id < 0 ? "ungrouped" : `group ${c.id}`} ({c.count})
                </span>
              </span>
            ))}
          </div>
          <svg viewBox={`0 0 ${width} ${height}`} className="block w-full">
            {scale &&
              points.map((p, i) => {
                const isActive = active?.song_id === p.song_id;
                const isNeighbour = neighbours.some((n) => n.song_id === p.song_id);
                const r = 4 + (p.play_count / maxPlays) * 13;
                return (
                  <g
                    key={p.song_id}
                    className="anim-pop-in cursor-pointer"
                    style={{ animationDelay: `${Math.min(i, 40) * 0.012}s` }}
                    onMouseEnter={() => setHovered(p.song_id)}
                    onMouseLeave={() => setHovered((h) => (h === p.song_id ? null : h))}
                    onClick={() => setSelected(p.song_id)}
                  >
                    <circle
                      cx={scale.x(p.x)}
                      cy={scale.y(p.y)}
                      r={r}
                      fill={scale.outside(p) ? "none" : colorFor(p.cluster_id)}
                      opacity={isActive ? 1 : isNeighbour ? 0.85 : active ? 0.25 : 0.65}
                      stroke={isActive ? "white" : scale.outside(p) ? colorFor(p.cluster_id) : "none"}
                      strokeWidth={isActive ? 1.5 : scale.outside(p) ? 1.5 : 0}
                      strokeDasharray={scale.outside(p) && !isActive ? "3 2" : undefined}
                    />
                    {(isActive || (!active && labelled.has(p.song_id))) && (
                      <text
                        x={scale.x(p.x)}
                        y={scale.y(p.y) - r - 5}
                        textAnchor="middle"
                        className="font-mono"
                        fontSize="9"
                        fill={isActive ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.45)"}
                      >
                        {p.song_name.length > 26 ? p.song_name.slice(0, 25) + "…" : p.song_name}
                      </text>
                    )}
                  </g>
                );
              })}
          </svg>
          <p className="mt-3 text-[13px] leading-relaxed text-white/30">
            Framed on the middle 96% of the coordinates so the dense centre stays readable.
            {outsideCount > 0
              ? ` ${outsideCount} song${outsideCount === 1 ? " sits" : "s sit"} outside that frame and ${outsideCount === 1 ? "is" : "are"} drawn hollow on the edge.`
              : ""}
          </p>
        </Card>

        <Card className="anim-fade-in-up col-span-5 lg:col-span-2" style={{ animationDelay: "0.1s" }}>
          {active ? (
            <>
              <div className="text-[13px] font-medium text-white/55">Selected song</div>
              <div className="mt-2 font-display text-2xl font-bold leading-tight">{active.song_name}</div>
              <div className="mt-3 flex items-center gap-2 font-mono text-xs text-white/50">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: colorFor(active.cluster_id) }} />
                {active.cluster_id < 0 ? "not grouped" : `group ${active.cluster_id}`} · played {active.play_count} times
              </div>

              <div className="text-[13px] font-medium mt-6 text-white/55">
                Closest on the map
              </div>
              <div className="mt-3 space-y-2">
                {neighbours.map((n) => (
                  <button
                    key={n.song_id}
                    type="button"
                    onClick={() => setSelected(n.song_id)}
                    className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-left transition-colors hover:border-white/30"
                  >
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: colorFor(n.cluster_id) }} />
                    <span className="min-w-0 flex-1 truncate font-display text-sm">{n.song_name}</span>
                    <span className="shrink-0 font-mono text-[10px] text-white/35">{n.play_count}x</span>
                  </button>
                ))}
              </div>
              <p className="mt-4 text-[13px] leading-relaxed text-white/30">
                Closeness here is distance on the stored map, which the clustering step built
                from songs appearing in the same setlists. It is not a claim about how the
                songs sound.
              </p>
            </>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-4 py-16 text-center text-white/30">
              <div className="h-24 w-24 rounded-full border-2 border-dashed border-white/20" />
              <p className="font-mono text-xs">Hover or click a song to see its neighbours</p>
            </div>
          )}
        </Card>

        <PhotoPanel
          photo={PHOTOS.synthTable}
          accent="ember"
          tag="songs that travel together"
          className="col-span-5 h-[19rem] lg:col-span-2"
          focus="center 30%"
        />
        <PhotoPanel
          photo={PHOTOS.roundStageOverhead}
          accent="ember"
          className="col-span-5 h-[19rem] lg:col-span-3"
          focus="center 30%"
          style={{ animationDelay: "0.08s" }}
        />
      </div>
    </div>
  );
}
