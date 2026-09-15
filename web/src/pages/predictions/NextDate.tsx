import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { NextDate as NextDateData } from "../../lib/types";

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function NextDate() {
  const [data, setData] = useState<NextDateData | null>(null);

  useEffect(() => {
    api.nextDate().then(setData).catch(() => {});
  }, []);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Next
          <br />
          Date
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">Predicted date of the next announced show</p>
      </div>
      {data && (
        <div className="mt-8 grid grid-cols-2 gap-6">
          <Card tinted>
            <div className="font-display text-5xl font-bold">{formatDate(data.predicted_date)}</div>
            <div className="mt-2 font-mono text-xs text-white/50">
              predicted mean — {data.days_from_today} days out
            </div>
            <div className="mt-6 flex gap-8">
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Mean abs. error</div>
                <div className="font-display text-xl font-bold">{data.mae_days} days</div>
              </div>
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Median abs. error</div>
                <div className="font-display text-xl font-bold">{data.median_absolute_error_days} days</div>
              </div>
            </div>
          </Card>
          <Card className="flex items-center justify-center border-dashed text-white/30">
            <p className="font-mono text-xs">[ photo placeholder ]</p>
          </Card>
        </div>
      )}
    </div>
  );
}
