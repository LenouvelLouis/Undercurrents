interface Stat {
  label: string;
  value: string;
}

export default function StatBar({ stats }: { stats: Stat[] }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 flex flex-wrap gap-x-8 gap-y-2 border-t border-white/10 bg-ink/90 px-8 py-3 backdrop-blur">
      {stats.map((stat) => (
        <span key={stat.label} className="font-mono text-xs text-white/50">
          {stat.label} <span className="font-bold text-white">{stat.value}</span>
        </span>
      ))}
    </div>
  );
}
