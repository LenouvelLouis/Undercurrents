import { useState } from "react";

export interface HeatmapAxisItem {
  key: string;
  label: string;
  sublabel?: string;
}

interface HeatmapProps {
  rows: HeatmapAxisItem[];
  cols: HeatmapAxisItem[];
  /** `${rowKey}|${colKey}` -> value. A missing key is an empty cell, not a zero. */
  values: Map<string, number>;
  maxValue: number;
  /** Text shown in the hover tooltip for a cell that has a value. */
  describe: (row: HeatmapAxisItem, col: HeatmapAxisItem, value: number) => string;
  /** Wording for the low and high ends of the scale legend. */
  legendLow?: string;
  legendHigh?: string;
  rowLabelWidth?: number;
  cellHeight?: number;
}

// Sequential ramp: one hue, climbing monotonically in lightness (OKLab L 0.16 -> 0.77)
// against the near-black chart surface. Single hue because these grids encode magnitude,
// where a rainbow would invent category boundaries the data does not have.
const RAMP = ["#1c0705", "#3a0f08", "#6b1a0c", "#9c2815", "#c63a22", "#e2492f", "#ff9270"];
const EMPTY_CELL = "rgba(255,255,255,0.035)";

function colorFor(value: number, maxValue: number) {
  if (value <= 0) return EMPTY_CELL;
  // sqrt keeps the long tail of small counts visible: play counts are heavily skewed, and
  // a linear ramp would render almost every cell at the dark end of the scale.
  const t = Math.sqrt(value / Math.max(maxValue, 1));
  const index = Math.min(RAMP.length - 1, Math.max(0, Math.round(t * (RAMP.length - 1))));
  return RAMP[index];
}

export default function Heatmap({
  rows,
  cols,
  values,
  maxValue,
  describe,
  legendLow = "fewer",
  legendHigh = "more",
  rowLabelWidth = 190,
  cellHeight = 22,
}: HeatmapProps) {
  const [hovered, setHovered] = useState<{ row: HeatmapAxisItem; col: HeatmapAxisItem; value: number } | null>(null);

  return (
    <div className="relative">
      <div className="overflow-x-auto pb-1">
        <div style={{ minWidth: rowLabelWidth + cols.length * 26 }}>
          {/* Column header */}
          <div className="flex items-end gap-[2px]" style={{ paddingLeft: rowLabelWidth }}>
            {cols.map((col) => (
              <div
                key={col.key}
                className="text-[11px] flex-1 pb-1 text-center text-white/50"
                style={{ minWidth: 20 }}
              >
                {col.label}
              </div>
            ))}
          </div>

          <div className="space-y-[2px]">
            {rows.map((row) => (
              <div key={row.key} className="flex items-center gap-[2px]">
                <div
                  className="shrink-0 truncate pr-3 text-right font-mono text-[10px] text-white/50"
                  style={{ width: rowLabelWidth }}
                  title={row.label}
                >
                  {row.label}
                  {row.sublabel && <span className="ml-2 text-white/25">{row.sublabel}</span>}
                </div>
                {cols.map((col) => {
                  const value = values.get(`${row.key}|${col.key}`) ?? 0;
                  const isHovered =
                    hovered?.row.key === row.key && hovered?.col.key === col.key;
                  return (
                    <div
                      key={col.key}
                      className="flex-1 cursor-default rounded-[3px] transition-[outline] duration-100"
                      style={{
                        minWidth: 20,
                        height: cellHeight,
                        backgroundColor: colorFor(value, maxValue),
                        outline: isHovered ? "2px solid rgba(255,255,255,0.85)" : "none",
                        outlineOffset: "-1px",
                      }}
                      onMouseEnter={() => setHovered({ row, col, value })}
                      onMouseLeave={() =>
                        setHovered((h) => (h && h.row.key === row.key && h.col.key === col.key ? null : h))
                      }
                    />
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Scale legend: always present, since colour is the only encoding of magnitude here. */}
      <div className="mt-4 flex items-center gap-3">
        <span className="text-[13px] font-medium text-white/50">{legendLow}</span>
        <div className="flex h-2 flex-1 max-w-[220px] overflow-hidden rounded-full">
          {RAMP.map((step) => (
            <div key={step} className="flex-1" style={{ backgroundColor: step }} />
          ))}
        </div>
        <span className="text-[13px] font-medium text-white/50">{legendHigh}</span>
        <span className="font-mono text-[10px] text-white/25">peak {maxValue}</span>
      </div>

      {/* Hover readout. Fixed position under the grid rather than following the cursor, so it
          never covers the cell being read. */}
      <div className="mt-3 min-h-[1.25rem] font-mono text-xs text-white/60">
        {hovered ? (
          hovered.value > 0 ? (
            describe(hovered.row, hovered.col, hovered.value)
          ) : (
            <span className="text-white/30">
              {hovered.row.label} · {hovered.col.label} · never
            </span>
          )
        ) : (
          <span className="text-white/25">Hover a cell for the exact figure</span>
        )}
      </div>
    </div>
  );
}
