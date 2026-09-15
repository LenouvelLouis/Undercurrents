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
            <defs>
              <filter id="cluster-glow" x="-100%" y="-100%" width="300%" height="300%">
                <feGaussianBlur stdDeviation="6" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
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
                  fill={selected ? "#d99a3f" : "#a531d6"}
                  opacity={selected ? 1 : 0.6}
                  filter={selected ? "url(#cluster-glow)" : undefined}
                  className="cursor-pointer transition-opacity"
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
            <div className="mt-3 flex flex-wrap gap-2">
              {detail.typical_songs.map((song) => (
                <span
                  key={song.song_id}
                  className="rounded-full border border-violet/40 bg-violet/10 px-3 py-1 font-display text-xs font-medium text-violet-light"
                >
                  {song.song_name}
                </span>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
