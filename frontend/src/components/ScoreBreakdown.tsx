import type { ScoreFactor } from "@shared/types";

export const FACTOR_NAME: Record<string, string> = {
  price: "Price",
  ion_proximity: "ION proximity",
  beds_match: "Bedrooms",
  term_match: "Term",
  geese: "Geese",
  highway: "Highway access",
  go_proximity: "GO proximity",
};

export const FACTOR_COLOR: Record<string, string> = {
  price: "#9C6B3F",
  ion_proximity: "#8A7060",
  beds_match: "#2B2A26",
  term_match: "#B79A76",
  geese: "#6B5F52",
  highway: "#A9927A",
  go_proximity: "#7A6A58",
};

/** Stacked bar whose segments add up to the total score (out of 100), plus
 *  one row per factor. Zero-point factors are listed so "why not higher" is
 *  visible too. */
export function ScoreBreakdown({ factors }: { factors: ScoreFactor[] }) {
  return (
    <>
      <div className="stack" role="img" aria-label="score breakdown">
        {factors
          .filter((f) => f.points > 0)
          .map((f) => (
            <div
              key={f.factor}
              title={`${FACTOR_NAME[f.factor] ?? f.factor}: +${f.points.toFixed(1)}`}
              style={{ width: `${f.points}%`, background: FACTOR_COLOR[f.factor] ?? "#8A7060" }}
            />
          ))}
      </div>
      <div className="factors">
        {factors.map((f) => (
          <div className="factor" key={f.factor}>
            <i style={{ background: FACTOR_COLOR[f.factor] ?? "#8A7060" }} />
            <span style={{ fontWeight: 500 }}>{FACTOR_NAME[f.factor] ?? f.factor}</span>
            <span className="muted">{f.explanation}</span>
            <span className="mono" style={{ textAlign: "right", color: f.points > 0 ? undefined : "var(--ink-4)" }}>
              +{f.points.toFixed(1)}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

/** Short chips for the card: the top factors that actually earned points. */
export const topReasons = (factors: ScoreFactor[], n = 3) =>
  [...factors].sort((a, b) => b.points - a.points).filter((f) => f.points > 0).slice(0, n).map((f) => f.label);
