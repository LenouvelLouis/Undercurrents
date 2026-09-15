import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { Venue } from "../../lib/types";

export default function VenueMap() {
  const [venues, setVenues] = useState<Venue[]>([]);

  useEffect(() => {
    api.venues().then(setVenues).catch(() => {});
  }, []);

  const maxShows = Math.max(...venues.map((v) => v.show_count), 1);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Venue
          <br />
          Map
        </h1>
        <p className="max-w-sm text-right font-mono text-xs italic text-white/40">
          {venues.length} venues · real geographic coordinates aren't available yet (see
          CLAUDE.md) — sorted by number of shows instead of plotted on a map
        </p>
      </div>
      <Card className="mt-8 max-h-[62vh] overflow-y-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 z-10 bg-bg font-mono text-xs uppercase tracking-widest text-white/40">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Venue</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3">Shows</th>
              <th className="px-4 py-3 text-right">Capacity</th>
              <th className="px-4 py-3 text-right">Last visited</th>
            </tr>
          </thead>
          <tbody>
            {venues.map((venue, i) => (
              <tr key={venue.id} className="border-t border-white/5 transition-colors hover:bg-ember/5">
                <td className="px-4 py-3 font-mono text-xs text-white/30">{String(i + 1).padStart(2, "0")}</td>
                <td className="px-4 py-3 font-medium">{venue.name}</td>
                <td className="px-4 py-3 text-white/60">{venue.city ?? "—"}</td>
                <td className="px-4 py-3 text-white/60">{venue.country ?? "—"}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/5">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-ember-dark to-ember"
                        style={{ width: `${Math.max(6, (venue.show_count / maxShows) * 100)}%` }}
                      />
                    </div>
                    <span className="font-mono text-xs text-white/60">{venue.show_count}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right text-white/60">{venue.capacity ?? "—"}</td>
                <td className="px-4 py-3 text-right text-white/60">{venue.last_visited ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
