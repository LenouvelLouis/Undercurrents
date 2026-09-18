import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import Heatmap, { type HeatmapAxisItem } from "../../components/Heatmap";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type {
  CalendarHeatmap,
  CooccurrenceHeatmap,
  SongPositionHeatmap,
  SongsByYearHeatmap,
} from "../../lib/types";

const MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];
const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const VIEWS = [
  { key: "years", label: "Songs by year" },
  { key: "calendar", label: "Touring calendar" },
  { key: "positions", label: "Where in the set" },
  { key: "cooccurrence", label: "Played together" },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

function shorten(name: string, max = 26) {
  return name.length > max ? name.slice(0, max - 1) + "…" : name;
}

export default function Heatmaps() {
  const [view, setView] = useState<ViewKey>("years");
  const [byYear, setByYear] = useState<SongsByYearHeatmap | null>(null);
  const [calendar, setCalendar] = useState<CalendarHeatmap | null>(null);
  const [positions, setPositions] = useState<SongPositionHeatmap | null>(null);
  const [cooccurrence, setCooccurrence] = useState<CooccurrenceHeatmap | null>(null);

  useEffect(() => {
    api.heatmapSongsByYear().then(setByYear).catch(() => {});
    api.heatmapCalendar().then(setCalendar).catch(() => {});
    api.heatmapSongPositions().then(setPositions).catch(() => {});
    api.heatmapCooccurrence().then(setCooccurrence).catch(() => {});
  }, []);

  const yearsGrid = useMemo(() => {
    if (!byYear) return null;
    const values = new Map<string, number>();
    let max = 0;
    for (const cell of byYear.cells) {
      values.set(`${cell.song_id}|${cell.year}`, cell.plays);
      max = Math.max(max, cell.plays);
    }
    return {
      rows: byYear.songs.map<HeatmapAxisItem>((s) => ({
        key: String(s.song_id),
        label: shorten(s.song_name),
        sublabel: String(s.plays),
      })),
      cols: byYear.years.map<HeatmapAxisItem>((y) => ({ key: String(y), label: String(y).slice(2) })),
      values,
      max,
    };
  }, [byYear]);

  const calendarGrid = useMemo(() => {
    if (!calendar) return null;
    const values = new Map<string, number>();
    let max = 0;
    for (const cell of calendar.cells) {
      values.set(`${cell.year}|${cell.month}`, cell.shows);
      max = Math.max(max, cell.shows);
    }
    return {
      rows: calendar.years.map<HeatmapAxisItem>((y) => ({ key: String(y), label: String(y) })),
      cols: MONTHS.map<HeatmapAxisItem>((m, i) => ({ key: String(i + 1), label: m })),
      values,
      max,
    };
  }, [calendar]);

  const positionsGrid = useMemo(() => {
    if (!positions) return null;
    const values = new Map<string, number>();
    let max = 0;
    for (const cell of positions.cells) {
      values.set(`${cell.song_id}|${cell.bucket}`, cell.plays);
      max = Math.max(max, cell.plays);
    }
    return {
      rows: positions.songs.map<HeatmapAxisItem>((s) => ({
        key: String(s.song_id),
        label: shorten(s.song_name),
        sublabel: String(s.plays),
      })),
      cols: Array.from({ length: positions.buckets }, (_, i) => ({
        key: String(i),
        label: i === 0 ? "open" : i === positions.buckets - 1 ? "close" : String(i + 1),
      })),
      values,
      max,
    };
  }, [positions]);

  const cooccurrenceGrid = useMemo(() => {
    if (!cooccurrence) return null;
    const values = new Map<string, number>();
    let max = 0;
    // The endpoint returns each unordered pair once; mirror it so the grid reads either way.
    for (const pair of cooccurrence.pairs) {
      values.set(`${pair.a_id}|${pair.b_id}`, pair.shows);
      values.set(`${pair.b_id}|${pair.a_id}`, pair.shows);
      max = Math.max(max, pair.shows);
    }
    // Diagonal: a song's own show count, so an off-diagonal cell can be read against it.
    for (const song of cooccurrence.songs) {
      values.set(`${song.song_id}|${song.song_id}`, song.shows);
    }
    const axis = cooccurrence.songs.map<HeatmapAxisItem>((s) => ({
      key: String(s.song_id),
      label: shorten(s.song_name, 24),
    }));
    return { rows: axis, cols: axis, values, max };
  }, [cooccurrence]);

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.roundStageAerial.src} alt={PHOTOS.roundStageAerial.alt} size={56} accent="ember" />
          <h1 className="font-display text-6xl font-bold">Heatmaps</h1>
        </div>
        <p className="max-w-sm text-right font-mono text-xs italic text-white/40">
          Four cross-tabs of the same 8,700 performances
          <br />
          colour is magnitude only, never category
        </p>
      </div>

      <div className="mt-8 flex flex-wrap gap-2">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            type="button"
            onClick={() => setView(v.key)}
            className={`rounded-full border px-4 py-2 font-mono text-xs uppercase tracking-widest transition-colors ${
              view === v.key
                ? "border-ember/60 bg-ember/15 text-white"
                : "border-white/15 text-white/50 hover:border-white/35 hover:text-white/80"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      <Card className="anim-fade-in-up mt-6" accent="ember">
        {view === "years" && (
          <>
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Songs by year
            </div>
            <p className="mt-2 max-w-2xl font-mono text-[11px] leading-relaxed text-white/35">
              Rows are the 40 most-played songs, columns are years. A dark row that suddenly
              lights up is a song entering the rotation; one that goes dark has been dropped.
            </p>
            <div className="mt-6">
              {yearsGrid ? (
                <Heatmap
                  rows={yearsGrid.rows}
                  cols={yearsGrid.cols}
                  values={yearsGrid.values}
                  maxValue={yearsGrid.max}
                  legendLow="rarely"
                  legendHigh="most nights"
                  describe={(row, col, value) =>
                    `${row.label} · ${col.key} · played ${value} time${value === 1 ? "" : "s"}`
                  }
                />
              ) : (
                <p className="font-mono text-xs text-white/30">Loading…</p>
              )}
            </div>
          </>
        )}

        {view === "calendar" && (
          <>
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Touring calendar
            </div>
            <p className="mt-2 max-w-2xl font-mono text-[11px] leading-relaxed text-white/35">
              Concerts per month, every year in the archive. The empty stretches are as
              informative as the busy ones: a blank row is a year off the road.
            </p>
            <div className="mt-6">
              {calendarGrid ? (
                <Heatmap
                  rows={calendarGrid.rows}
                  cols={calendarGrid.cols}
                  values={calendarGrid.values}
                  maxValue={calendarGrid.max}
                  legendLow="quiet"
                  legendHigh="busiest"
                  rowLabelWidth={70}
                  cellHeight={26}
                  describe={(row, col, value) =>
                    `${MONTH_NAMES[Number(col.key) - 1]} ${row.label} · ${value} show${value === 1 ? "" : "s"}`
                  }
                />
              ) : (
                <p className="font-mono text-xs text-white/30">Loading…</p>
              )}
            </div>
          </>
        )}

        {view === "positions" && (
          <>
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Where in the set
            </div>
            <p className="mt-2 max-w-2xl font-mono text-[11px] leading-relaxed text-white/35">
              Each show's running order is normalised into ten slots, so a 12-song night and a
              22-song night line up. Encores land in the closing slots by construction, which
              is why the right-hand column is where the set-closers cluster.
            </p>
            <div className="mt-6">
              {positionsGrid ? (
                <Heatmap
                  rows={positionsGrid.rows}
                  cols={positionsGrid.cols}
                  values={positionsGrid.values}
                  maxValue={positionsGrid.max}
                  legendLow="seldom here"
                  legendHigh="usually here"
                  cellHeight={22}
                  describe={(row, col, value) =>
                    `${row.label} · slot ${Number(col.key) + 1} of 10 · ${value} time${value === 1 ? "" : "s"}`
                  }
                />
              ) : (
                <p className="font-mono text-xs text-white/30">Loading…</p>
              )}
            </div>
          </>
        )}

        {view === "cooccurrence" && (
          <>
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Played together
            </div>
            <p className="mt-2 max-w-2xl font-mono text-[11px] leading-relaxed text-white/35">
              How many shows contain both songs, for the 28 most-played. The diagonal is each
              song's own show count, so an off-diagonal cell can be read against it. This is
              the raw material the Song Map is built from, before any projection.
            </p>
            <div className="mt-6">
              {cooccurrenceGrid ? (
                <Heatmap
                  rows={cooccurrenceGrid.rows}
                  cols={cooccurrenceGrid.cols}
                  values={cooccurrenceGrid.values}
                  maxValue={cooccurrenceGrid.max}
                  legendLow="rarely both"
                  legendHigh="nearly always both"
                  rowLabelWidth={180}
                  cellHeight={20}
                  describe={(row, col, value) =>
                    row.key === col.key
                      ? `${row.label} · played at ${value} shows in total`
                      : `${row.label} + ${col.label} · together at ${value} shows`
                  }
                />
              ) : (
                <p className="font-mono text-xs text-white/30">Loading…</p>
              )}
            </div>
          </>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.roundStageAerial}
          accent="ember"
          tag="eighteen years, one grid"
          className="col-span-3 h-[19rem] lg:col-span-2"
          focus="center 35%"
        />
        <PhotoPanel
          photo={PHOTOS.synthTable}
          accent="ember"
          className="col-span-3 h-[19rem] lg:col-span-1"
          focus="center 30%"
          style={{ animationDelay: "0.08s" }}
        />
      </div>
    </div>
  );
}
