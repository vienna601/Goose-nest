import type { ScoreWeights } from "@shared/types";
import { WEIGHT_ROWS } from "../lib/prefs";

const STEPS = [
  { label: "Not", v: 0 },
  { label: "Somewhat", v: 0.5 },
  { label: "Very", v: 1 },
];

/** Nearest 3-step bucket, so the 0.25 defaults still highlight "Somewhat". */
const bucket = (w: number) => (w <= 0 ? 0 : w < 0.75 ? 0.5 : 1);

export function WeightsPanel({ weights, setWeight }: { weights: ScoreWeights; setWeight: (k: keyof ScoreWeights, v: number) => void }) {
  return (
    <div className="weights">
      <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 4 }}>
        What matters to you? This changes how we rank — not what we show.
      </div>
      {WEIGHT_ROWS.map((row) => (
        <div className="weight-row" key={row.key}>
          <span>{row.label}</span>
          <div className="seg" role="group" aria-label={`${row.label} importance`}>
            {STEPS.map((s) => (
              <button key={s.v} className="seg-opt sm" aria-pressed={bucket(weights[row.key]) === s.v} onClick={() => setWeight(row.key, s.v)}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
