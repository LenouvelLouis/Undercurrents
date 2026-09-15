import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { ClusterDetail, ClusterSummary } from "../../lib/types";

export default function ClusterExplorer() {
  const [clusters, setClusters] = useState<ClusterSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ClusterDetail | null>(null);

  useEffect(() => {
    api.clusters().then((data) => {
      setClusters(data);
      if (data.length > 0) setSelectedId(data[0].cluster_id);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selectedId !== null) {
      api.clusterDetail(selectedId).then(setDetail).catch(() => {});
    }
  }, [selectedId]);

  const maxSize = Math.max(...clusters.map((c) => c.size), 1);
  const center = 220;

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Cluster
          <br />
          Explorer
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          {clusters.length} setlist clusters in orbit
          <br />
          dot size = concerts in cluster
        </p>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-6">
        <Card className="flex items-center justify-center">
          <svg viewBox="0 0 440 440" width="440" height="440">
            {[1, 2, 3].map((ring) => (
              <circle key={ring} cx={center} cy={center} r={(ring / 3) * 180} fill="none" stroke="rgba(255,255,255,0.06)" />
            ))}
            {clusters.map((cluster, i) => {
              const angle = (i / clusters.length) * Math.PI * 2;
              const ringRadius = 60 + (i % 3) * 60;
              const cx = center + Math.cos(angle) * ringRadius;
              const cy = center + Math.sin(angle) * ringRadius;
              const r = 4 + (cluster.size / maxSize) * 16;
              const selected = cluster.cluster_id === selectedId;
              return (
                <circle
                  key={cluster.cluster_id}
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill={selected ? "#f97316" : "#c026d3"}
                  opacity={selected ? 1 : 0.6}
                  className="cursor-pointer"
                  onClick={() => setSelectedId(cluster.cluster_id)}
                />
              );
            })}
          </svg>
        </Card>
        {detail && (
          <Card>
            <div className="font-mono text-xs uppercase tracking-widest text-white/40">
              Cluster C{String(detail.cluster_id).padStart(2, "0")}
            </div>
            <div className="mt-1 font-display text-5xl font-bold">{detail.size}</div>
            <div className="font-mono text-xs text-white/50">concerts in this cluster</div>
            <div className="mt-4 font-mono text-xs text-white/40">Dominant period — {detail.dominant_period} era</div>
            <div className="mt-6 font-mono text-xs uppercase tracking-widest text-white/40">Typical songs</div>
            <ul className="mt-2 space-y-1">
              {detail.typical_songs.map((song) => (
                <li key={song.song_id} className="font-display font-medium">{song.song_name}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}
