import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { ClusterDetail, ClusterSummary } from "../../lib/types";

// Same era palette used on Setlist Trend, so a cluster's dominant era reads as the
// same color everywhere in the app.
const ERA_COLORS: Record<string, string> = {
  Innerspeaker: "#d99a3f",
  Lonerism: "#e2492f",
  Currents: "#a531d6",
  "Slow Rush -> Deadbeat": "#ff9270",
};

function parseDate(iso: string) {
  return new Date(iso + "T00:00:00").getTime();
}

function formatShort(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

const ZOOM_MIN = 0.75;
const ZOOM_MAX = 2.5;
const ZOOM_STEP = 0.25;

export default function ClusterExplorer() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ClusterDetail | null>(null);
  const [zoomLevel, setZoomLevel] = useState(1);

  useEffect(() => {
    api
      .clusters()
      .then((data) => {
        setClusters(data);
        if (data.length > 0) setSelectedId(data[0].cluster_id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedId !== null) {
      api.clusterDetail(selectedId).then(setDetail).catch(() => {});
    }
  }, [selectedId]);

  const ordered = useMemo(
    () => clusters.slice().sort((a, b) => parseDate(a.date_start) - parseDate(b.date_start)),
    [clusters],
  );

  const maxSize = Math.max(...clusters.map((c) => c.size), 1);

  // Real chronological axis: each cluster's actual date_start/date_end range is
  // plotted directly, rather than laid out on a decorative orbit.
  const { minT, maxT, yearTicks } = useMemo(() => {
    if (ordered.length === 0) return { minT: 0, maxT: 1, yearTicks: [] as number[] };
    const starts = ordered.map((c) => parseDate(c.date_start));
    const ends = ordered.map((c) => parseDate(c.date_end));
    const lo = Math.min(...starts);
    const hi = Math.max(...ends);
    const loYear = new Date(lo).getFullYear();
    const hiYear = new Date(hi).getFullYear();
    const ticks: number[] = [];
    for (let y = loYear; y <= hiYear; y++) ticks.push(new Date(`${y}-01-01T00:00:00`).getTime());
    return { minT: lo, maxT: hi, yearTicks: ticks };
  }, [ordered]);

  // width is fixed in viewBox units and the SVG renders at the card's full CSS width
  // (no explicit CSS height, so the browser derives it from the viewBox's own aspect
  // ratio). That pins the px-per-unit scale factor to the card width alone, so growing
  // rowHeight in viewBox units grows every row (bars, labels, spacing together, since
  // they share the same coordinate system) by that same factor on screen: real zoom,
  // not a blurry CSS transform. The card scrolls vertically once content outgrows it.
  const width = 720;
  const padLeft = 46;
  const padRight = 20;
  const rowHeight = 26 * zoomLevel;
  const padTop = 14;
  const padBottom = 24;
  const plotWidth = width - padLeft - padRight;
  const height = padTop + ordered.length * rowHeight + padBottom;
  const span = maxT - minT || 1;
  const xAt = (t: number) => padLeft + ((t - minT) / span) * plotWidth;

  const eraEntries = Object.entries(ERA_COLORS);

  // Real counts and average size per era, aggregated from the same cluster list the
  // timeline above already plots.
  const eraBreakdown = useMemo(() => {
    const map = new Map<string, { count: number; totalSize: number }>();
    for (const c of clusters) {
      const entry = map.get(c.dominant_period) ?? { count: 0, totalSize: 0 };
      entry.count += 1;
      entry.totalSize += c.size;
      map.set(c.dominant_period, entry);
    }
    return eraEntries
      .map(([era, color]) => {
        const agg = map.get(era);
        return { era, color, count: agg?.count ?? 0, avgSize: agg ? agg.totalSize / agg.count : 0 };
      })
      .filter((e) => e.count > 0);
  }, [clusters, eraEntries]);
  const maxEraCount = Math.max(...eraBreakdown.map((e) => e.count), 1);

  return (
    <div>
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.roundStageOverhead.src} alt={PHOTOS.roundStageOverhead.alt} size={56} accent="violet" />
          <h1 className="font-display text-6xl font-bold">
            Cluster
            <br />
            Explorer
          </h1>
        </div>
        <p className="text-right font-mono text-xs italic text-white/40">
          {clusters.length} setlist clusters across the timeline
          <br />
          bar span = active date range · width = concerts in cluster
        </p>
      </div>
      <div className="mt-10 grid grid-cols-5 gap-6">
        <Card className="anim-fade-in-up col-span-5 overflow-hidden lg:col-span-3">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              {eraEntries.map(([era, color]) => (
                <div key={era} className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="font-mono text-[10px] uppercase tracking-widest text-white/40">{era}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))}
                disabled={zoomLevel <= ZOOM_MIN}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-white/15 font-mono text-xs text-white/60 transition-colors hover:border-violet/50 hover:text-white disabled:opacity-30"
                aria-label="Zoom out"
              >
                −
              </button>
              <span className="w-9 text-center font-mono text-[10px] text-white/40">{Math.round(zoomLevel * 100)}%</span>
              <button
                type="button"
                onClick={() => setZoomLevel((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))}
                disabled={zoomLevel >= ZOOM_MAX}
                className="flex h-6 w-6 items-center justify-center rounded-md border border-white/15 font-mono text-xs text-white/60 transition-colors hover:border-violet/50 hover:text-white disabled:opacity-30"
                aria-label="Zoom in"
              >
                +
              </button>
            </div>
          </div>
          <div className="max-h-[680px] overflow-y-auto pr-1">
          <svg viewBox={`0 0 ${width} ${height}`} className="block w-full">
            <defs>
              <filter id="cluster-glow" x="-100%" y="-100%" width="300%" height="300%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {yearTicks.map((t) => (
              <g key={t}>
                <line x1={xAt(t)} y1={padTop - 4} x2={xAt(t)} y2={height - padBottom} stroke="rgba(255,255,255,0.06)" />
                <text x={xAt(t)} y={height - padBottom + 14} textAnchor="middle" className="font-mono" fontSize={9 * zoomLevel} fill="rgba(255,255,255,0.3)">
                  {new Date(t).getFullYear()}
                </text>
              </g>
            ))}

            {ordered.map((cluster, i) => {
              const y = padTop + i * rowHeight + rowHeight / 2;
              const x0 = xAt(parseDate(cluster.date_start));
              const x1 = xAt(parseDate(cluster.date_end));
              const barW = Math.max(6, x1 - x0);
              const barH = (8 + (cluster.size / maxSize) * 14) * zoomLevel;
              const color = ERA_COLORS[cluster.dominant_period] ?? "#a531d6";
              const selected = cluster.cluster_id === selectedId;
              const hovered = cluster.cluster_id === hoveredId;
              return (
                <g
                  key={cluster.cluster_id}
                  className="anim-bar-in cursor-pointer"
                  style={{ animationDelay: `${i * 0.02}s` }}
                  onClick={() => setSelectedId(cluster.cluster_id)}
                  onMouseEnter={() => setHoveredId(cluster.cluster_id)}
                  onMouseLeave={() => setHoveredId((h) => (h === cluster.cluster_id ? null : h))}
                >
                  <text x={padLeft - 8} y={y + 3} textAnchor="end" className="font-mono" fontSize={9 * zoomLevel} fill="rgba(255,255,255,0.3)">
                    C{String(cluster.cluster_id).padStart(2, "0")}
                  </text>
                  <rect
                    x={x0}
                    y={y - barH / 2}
                    width={barW}
                    height={barH}
                    rx={barH / 2}
                    fill={color}
                    opacity={selected ? 1 : hovered ? 0.85 : 0.55}
                    stroke={selected ? "white" : "none"}
                    strokeWidth={selected ? 1 : 0}
                    filter={selected ? "url(#cluster-glow)" : undefined}
                  />
                  <text
                    x={x0 + barW + 6}
                    y={y + 3}
                    className="font-mono"
                    fontSize={9 * zoomLevel}
                    fill={selected || hovered ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.35)"}
                  >
                    {cluster.size}
                  </text>
                </g>
              );
            })}
          </svg>
          </div>
        </Card>
        {detail && (
          <Card className="anim-fade-in-up col-span-5 lg:col-span-2" style={{ animationDelay: "0.1s" }}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">
                  Cluster C{String(detail.cluster_id).padStart(2, "0")}
                </div>
                <div className="mt-1 font-display text-5xl font-bold">{detail.size}</div>
                <div className="font-mono text-xs text-white/50">concerts in this cluster</div>
              </div>
              <PhotoChip
                src={PHOTOS.stageRainbowLights.src}
                alt={PHOTOS.stageRainbowLights.alt}
                size={44}
                accent="violet"
                className="shrink-0"
              />
            </div>
            <div className="mt-4 flex items-center gap-2 font-mono text-xs text-white/40">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: ERA_COLORS[detail.dominant_period] ?? "#a531d6" }} />
              {detail.dominant_period} era · {formatShort(detail.date_start)} – {formatShort(detail.date_end)}
            </div>
            <div className="mt-6 font-mono text-xs uppercase tracking-widest text-white/40">Typical songs</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {detail.typical_songs.map((song, i) => (
                <span
                  key={song.song_id}
                  className="anim-pop-in rounded-full border border-violet/40 bg-violet/10 px-3 py-1 font-display text-xs font-medium text-violet-light"
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  {song.song_name}
                </span>
              ))}
            </div>
          </Card>
        )}
      </div>

      <Card className="anim-fade-in-up mt-6">
        <div className="font-mono text-xs uppercase tracking-widest text-white/40">Clusters by dominant era</div>
        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {eraBreakdown.map((e, i) => (
            <div key={e.era} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.06}s` }}>
              <div className="flex items-center justify-between font-mono text-xs text-white/60">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: e.color }} />
                  {e.era}
                </span>
                <span>{e.count} cluster{e.count === 1 ? "" : "s"}</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className="anim-width-in h-full rounded-full"
                  style={{ width: `${(e.count / maxEraCount) * 100}%`, backgroundColor: e.color, animationDelay: `${0.1 + i * 0.05}s` }}
                />
              </div>
              <div className="mt-1 font-mono text-[10px] text-white/30">avg {e.avgSize.toFixed(1)} concerts / cluster</div>
            </div>
          ))}
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.roundStageOverhead}
          accent="violet"
          tag="one night, one cluster"
          className="col-span-3 h-[20rem] lg:col-span-1"
          focus="center 28%"
        />
        <PhotoPanel
          photo={PHOTOS.stageRainbowLights}
          accent="violet"
          className="col-span-3 h-[20rem] lg:col-span-1"
          focus="center 40%"
          style={{ animationDelay: "0.08s" }}
        />
        <PhotoPanel
          photo={PHOTOS.roundStageAerial}
          accent="violet"
          className="col-span-3 h-[20rem] lg:col-span-1"
          focus="center 35%"
          style={{ animationDelay: "0.16s" }}
        />
      </div>
    </div>
  );
}
