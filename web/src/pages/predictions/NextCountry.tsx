import { useEffect, useState } from "react";
import Card from "../../components/Card";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import type { CountryPrediction } from "../../lib/types";

export default function NextCountry() {
  const [predictions, setPredictions] = useState<CountryPrediction[]>([]);

  useEffect(() => {
    api.nextCountry().then(setPredictions).catch(() => {});
  }, []);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Next
          <br />
          Country
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Ranked probability across {predictions.length} countries played
        </p>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-6">
        <Card className="space-y-4">
          {predictions.slice(0, 8).map((prediction) => (
            <div key={prediction.country}>
              <div className="flex justify-between font-mono text-xs text-white/60">
                <span>{prediction.country}</span>
                <span>{Math.round(prediction.probability * 100)}%</span>
              </div>
              <ProgressBar percentage={prediction.probability * 100} />
            </div>
          ))}
        </Card>
        <Card className="flex items-center justify-center border-dashed text-white/30">
          <p className="font-mono text-xs">top-5 preview — stylized outline</p>
        </Card>
      </div>
    </div>
  );
}
