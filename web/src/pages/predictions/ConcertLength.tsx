import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { SetlistLength } from "../../lib/types";

export default function ConcertLength() {
  const [length, setLength] = useState<SetlistLength | null>(null);

  useEffect(() => {
    api.setlistLength().then(setLength).catch(() => {});
  }, []);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Concert
          <br />
          Length
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Predicted song count for the next show
        </p>
      </div>
      <Card tinted className="mt-8 flex w-fit flex-col items-center px-16 py-12">
        <span className="font-display text-7xl font-bold">{length?.predicted_songs ?? "—"}</span>
        <span className="font-mono text-xs uppercase tracking-widest text-white/50">songs (mean)</span>
      </Card>
    </div>
  );
}
