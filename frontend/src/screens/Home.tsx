import { useState } from "react";
import type { ScoreWeights } from "@shared/types";
import { gooseWord, money } from "../lib/format";
import { PRICE_CEIL, WALK_CEIL, type Prefs } from "../lib/prefs";
import { GOOSE_PATH } from "../components/Goose";
import { WeightsPanel } from "./WeightsPanel";

export interface Stats {
  total: number;
  medianPrice: number | null;
  medianWalk: number | null;
  medianGeese: number | null;
}

interface Props {
  prefs: Prefs;
  setPref: <K extends keyof Prefs>(k: K, v: Prefs[K]) => void;
  weights: ScoreWeights;
  setWeight: (k: keyof ScoreWeights, v: number) => void;
  matchCount: number | null;
  stats: Stats | null;
  apiError: string | null;
  onSearch: () => void;
}

function Seg<T extends string | number | null>({ opts, value, onPick, mono }: { opts: { label: string; v: T }[]; value: T; onPick: (v: T) => void; mono?: boolean }) {
  return (
    <div className="seg">
      {opts.map((o) => (
        <button key={String(o.v)} className={`seg-opt${mono ? " mono" : ""}`} aria-pressed={value === o.v} onClick={() => onPick(o.v)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Home({ prefs: p, setPref, weights, setWeight, matchCount, stats, apiError, onSearch }: Props) {
  const [tuneOpen, setTuneOpen] = useState(false);
  const total = stats?.total;

  return (
    <div className="page home">
      <div className="rise">
        <div className="hero-badge">Waterloo · Kitchener{total ? ` · ${total} live listings` : ""}</div>
        <h1 className="h1">Student housing, ranked&nbsp;by what you&nbsp;actually care&nbsp;about.</h1>
        <p className="lede">
          Tell us your term, your budget, your walk to the ION — and your tolerance for geese. We shortlist the nests, then
          an agent fills out the landlord's form for you and waits for your approval before sending anything.
        </p>

        <div className="prefs">
          <div className="eyebrow" style={{ fontFamily: "var(--display)", fontSize: 13, letterSpacing: ".1em", marginBottom: 20 }}>
            Preference form
          </div>

          <div className="prefs-grid">
            <div>
              <div className="eyebrow" style={{ marginBottom: 8 }}>What are you renting</div>
              <Seg opts={[{ label: "Room", v: "room" as const }, { label: "Whole unit", v: "unit" as const }]} value={p.kind} onPick={(v) => setPref("kind", v)} />
            </div>
            <div>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Lease type</div>
              <Seg
                opts={[{ label: "Lease", v: "lease" as const }, { label: "Sublet", v: "sublet" as const }, { label: "Either", v: "either" as const }]}
                value={p.lease}
                onPick={(v) => setPref("lease", v)}
              />
            </div>
            <div>
              <div className="eyebrow" style={{ marginBottom: 8 }}>Term length</div>
              <Seg
                mono
                opts={[{ label: "4 mo", v: 4 as number | "any" }, { label: "8 mo", v: 8 }, { label: "12 mo", v: 12 }, { label: "Any", v: "any" }]}
                value={p.term}
                onPick={(v) => setPref("term", v)}
              />
            </div>
            <label className="field">
              <span className="eyebrow">Available by</span>
              <input type="date" className="input" value={p.availableBy} onChange={(e) => setPref("availableBy", e.target.value)} />
            </label>

            <label>
              <div className="range-head">
                <span className="eyebrow">Budget</span>
                <span className="range-val">{p.priceMax >= PRICE_CEIL ? "Any" : money(p.priceMax) + "/mo"}</span>
              </div>
              <input type="range" min={500} max={PRICE_CEIL} step={25} value={p.priceMax} onChange={(e) => setPref("priceMax", +e.target.value)} />
            </label>
            <label>
              <div className="range-head">
                <span className="eyebrow">Walk to ION</span>
                <span className="range-val">{p.walkMax >= WALK_CEIL ? "Any" : p.walkMax + " min"}</span>
              </div>
              <input type="range" min={3} max={WALK_CEIL} step={1} value={p.walkMax} onChange={(e) => setPref("walkMax", +e.target.value)} />
            </label>
          </div>

          <div className="goose-box">
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Geese tolerance</div>
              <div style={{ fontSize: 14, color: "var(--ink-2)" }}>
                Up to {p.gooseMax}/5 — {gooseWord(p.gooseMax)}
              </div>
            </div>
            <div className="row" style={{ gap: 8 }} role="group" aria-label="Maximum goose score">
              {[1, 2, 3, 4, 5].map((g) => (
                <button key={g} className="goose-opt" title={gooseWord(g)} aria-label={`${g}: ${gooseWord(g)}`} aria-pressed={g <= p.gooseMax} onClick={() => setPref("gooseMax", g)}>
                  <span style={{ width: 6 + g * 2, height: 6 + g * 2, animationDelay: `${g * 0.04}s` }} />
                </button>
              ))}
            </div>
          </div>

          <div className="row wrap" style={{ marginTop: 18, gap: 12 }}>
            <button className="pill-toggle" aria-pressed={p.triCity} onClick={() => setPref("triCity", !p.triCity)}>
              Include Kitchener &amp; Cambridge
            </button>
            <button className="pill-toggle btn-link" onClick={() => setTuneOpen(!tuneOpen)} aria-expanded={tuneOpen}>
              {tuneOpen ? "Hide ranking weights" : "Tune ranking"}
            </button>
          </div>

          {tuneOpen && <WeightsPanel weights={weights} setWeight={setWeight} />}

          <button className="btn-cta btn-block btn-lg" style={{ marginTop: 24 }} onClick={onSearch}>
            Find my nest →
          </button>
          <div style={{ marginTop: 10, textAlign: "center", fontSize: 12, color: apiError ? "#8E3B2A" : "var(--ink-3)" }}>
            {apiError ?? (matchCount == null ? "Checking the nests…" : `${matchCount}${total ? ` of ${total}` : ""} listings match right now`)}
          </div>
        </div>
      </div>

      <GooseArt stats={stats} />
    </div>
  );
}

// The design's hero: a big goose built out of little geese.
const ART_MASK = [
  "................hhh.....", "...............hhhhh....", "...............hehhh....", "...............hhhhhkkk.",
  "...............hcchhkkkk", "...............hccchh...", "...............hhchh....", "...............hhhh.....",
  "...............hhhh.....", "...............hhhh.....", "...............hhhh.....", "..............hhhhh.....",
  "..............hhhhh.....", "........gggggghhhhww....", ".....ggggggggggggwwww...", "...gggggggggggggggwww...",
  "..ggggggggggggggggwwww..", ".wggggggggggggggwwwwww..", "wwwgggggggggggwwwwwwww..", ".wwwwwwwwwwwwwwwwwwww...",
  "..wwwwwwwwwwwwwwwwwww...", "...wwwwwwwwwwwwwwwww....", ".....wwwwwwwwwwwwww.....", "........wwwwwwwwww......",
  "..........ll..ll........", "..........ll..ll........", ".........lll.lll........",
];
const PALETTE: Record<string, string> = { h: "#2E2E2E", k: "#4A4A4A", c: "#FBF3E4", g: "#8A7060", w: "#F2E6D2", l: "#3F3F3F", e: "#FFFFFF" };
const rand = (i: number, m: number) => ((i * 9301 + 49297) % m) / m;

function GooseArt({ stats }: { stats: Stats | null }) {
  return (
    <div className="art-wrap" aria-hidden="true">
      <div className="art">
        {Array.from({ length: 14 }, (_, i) => (
          <span
            key={i}
            className="bubble"
            style={{
              top: `${(rand(i + 1, 17) * 92 + 2).toFixed(0)}%`, left: `${(rand(i + 5, 13) * 90 + 3).toFixed(0)}%`,
              width: 5 + rand(i, 5) * 9, height: 5 + rand(i, 5) * 9,
              animation: `gnPulse ${(2.4 + rand(i + 2, 9) * 3).toFixed(1)}s infinite ${(rand(i + 7, 11) * 2.4).toFixed(1)}s`,
            }}
          />
        ))}
        <div className="art-grid">
          {ART_MASK.map((row, r) => (
            <div className="art-row" key={r}>
              {row.split("").map((ch, c) => {
                const i = r * 25 + c;
                const blink = ch !== "." && i % 5 === 0;
                return (
                  <span
                    key={c}
                    className="art-cell"
                    style={blink ? { animation: `gnBlink ${(2.6 + rand(i, 7) * 3).toFixed(1)}s infinite ${(rand(i + 3, 11) * 3).toFixed(1)}s` } : undefined}
                  >
                    {ch !== "." && (
                      <svg viewBox="0 0 12 12">
                        <path d={GOOSE_PATH} fill={PALETTE[ch] ?? "#8A7060"} stroke="#2E2E2E" strokeWidth="0.7" />
                        <circle cx="8.9" cy="3" r="0.5" fill="#2E2E2E" />
                      </svg>
                    )}
                  </span>
                );
              })}
            </div>
          ))}
        </div>
        <div className="kicker" style={{ position: "relative", marginTop: 18, textAlign: "center", fontSize: 10.5, letterSpacing: ".14em" }}>
          Goose scores from iNaturalist sightings within 500 m
        </div>
      </div>
      <div className="stats">
        <div className="stat"><b>{stats?.medianPrice != null ? money(stats.medianPrice) : "—"}</b><span>median rent</span></div>
        <div className="stat"><b>{stats?.medianWalk != null ? `${stats.medianWalk} min` : "—"}</b><span>median ION walk</span></div>
        <div className="stat"><b>{stats?.medianGeese != null ? stats.medianGeese.toFixed(1) : "—"}</b><span>median geese</span></div>
      </div>
    </div>
  );
}

