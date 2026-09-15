import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { Venue } from "../../lib/types";

export default function VenueMap() {
  const [venues, setVenues] = useState<Venue[]>([]);

  useEffect(() => {
    api.venues().then(setVenues).catch(() => {});
  }, []);

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
      <Card className="mt-8 max-h-[60vh] overflow-y-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="sticky top-0 bg-bg font-mono text-xs uppercase tracking-widest text-white/40">
            <tr>
              <th className="px-4 py-3">Venue</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3 text-right">Shows</th>
              <th className="px-4 py-3 text-right">Capacity</th>
              <th className="px-4 py-3 text-right">Last visited</th>
            </tr>
          </thead>
          <tbody>
            {venues.map((venue) => (
              <tr key={venue.id} className="border-t border-white/5 hover:bg-white/5">
                <td className="px-4 py-2 font-medium">{venue.name}</td>
                <td className="px-4 py-2 text-white/60">{venue.city ?? "—"}</td>
                <td className="px-4 py-2 text-white/60">{venue.country ?? "—"}</td>
                <td className="px-4 py-2 text-right">{venue.show_count}</td>
                <td className="px-4 py-2 text-right text-white/60">{venue.capacity ?? "—"}</td>
                <td className="px-4 py-2 text-right text-white/60">{venue.last_visited ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
