import { useEffect, useState } from "react";
import { sourceLabel } from "../lib/format";
import type { Source } from "@shared/types";

/** Shown while POST /search is in flight. The backend doesn't stream
 *  collection_progress yet, so each source's bar fills over the request and
 *  snaps to done when results land. Counts are the real inventory per source. */
export function Searching({ bySource, done }: { bySource: Partial<Record<Source, number>>; done: boolean }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 180);
    return () => clearInterval(t);
  }, []);

  const sources = Object.entries(bySource) as [Source, number][];
  const rows = sources.length ? sources : ([["bamboo", 0], ["rent_panda", 0]] as [Source, number][]);

  return (
    <div className="searching">
      <div className="h2" style={{ fontSize: 34 }}>Counting geese…</div>
      <div style={{ marginTop: 28, display: "grid", gap: 16 }}>
        {rows.map(([src, total], i) => {
          const pct = done ? 100 : Math.min(92, Math.max(0, tick * 9 - i * 25));
          const fetched = total ? Math.round((total * pct) / 100) : null;
          return (
            <div key={src}>
              <div className="row mono" style={{ justifyContent: "space-between", fontSize: 12, color: "var(--ink-2)", marginBottom: 6 }}>
                <span>{sourceLabel(src)}</span>
                <span>{fetched != null ? `${fetched} / ${total}` : "…"}</span>
              </div>
              <div className="bar">
                <div style={{ width: `${pct}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
