import { useMemo, useState } from "react";
import type { ScoredListing, ScoreWeights } from "@shared/types";
import { money, shortAddress } from "../lib/format";
import { DEFAULT_PREFS, PRICE_CEIL, WALK_CEIL, type Prefs } from "../lib/prefs";
import { ListingCard } from "../components/ListingCard";
import { MapView } from "../components/MapView";
import { GooseRow } from "../components/Goose";
import { WeightsPanel } from "./WeightsPanel";

type Sort = "best" | "price" | "ion" | "geese";
type View = "list" | "split" | "map";

interface Props {
  results: ScoredListing[] | null;
  loading: boolean;
  error: string | null;
  prefs: Prefs;
  setPref: <K extends keyof Prefs>(k: K, v: Prefs[K]) => void;
  weights: ScoreWeights;
  setWeight: (k: keyof ScoreWeights, v: number) => void;
  shortlist: ScoredListing[];
  toggleShortlist: (item: ScoredListing) => void;
  openDetail: (item: ScoredListing) => void;
  startContact: () => void;
  retry: () => void;
}

const nullLast = (v: number | null) => (v == null ? Number.POSITIVE_INFINITY : v);

export function Results(props: Props) {
  const { results, loading, error, prefs: p, setPref, shortlist } = props;
  const [sort, setSort] = useState<Sort>("best");
  const [view, setView] = useState<View>(() => (window.innerWidth < 1080 ? "list" : "split"));
  const [hovered, setHovered] = useState<string | null>(null);
  const [tuneOpen, setTuneOpen] = useState(false);

  const sorted = useMemo(() => {
    const out = [...(results ?? [])];
    const by = {
      best: (a: ScoredListing, b: ScoredListing) => b.score - a.score,
      price: (a: ScoredListing, b: ScoredListing) => nullLast(a.listing.price_min) - nullLast(b.listing.price_min),
      ion: (a: ScoredListing, b: ScoredListing) => nullLast(a.listing.ion_walk_min) - nullLast(b.listing.ion_walk_min),
      geese: (a: ScoredListing, b: ScoredListing) => nullLast(a.listing.geese_score) - nullLast(b.listing.geese_score),
    }[sort];
    return out.sort(by);
  }, [results, sort]);

  // Removable chips. Clearing one widens that filter to "any".
  const chips: { label: string; clear: () => void }[] = [];
  if (p.kind) chips.push({ label: p.kind === "room" ? "Room" : "Whole unit", clear: () => setPref("kind", null) });
  if (p.lease !== "either") chips.push({ label: p.lease === "sublet" ? "Sublet" : "Lease", clear: () => setPref("lease", "either") });
  if (p.term !== "any") chips.push({ label: `${p.term} months`, clear: () => setPref("term", "any") });
  if (p.priceMax < PRICE_CEIL) chips.push({ label: `≤ ${money(p.priceMax)}`, clear: () => setPref("priceMax", PRICE_CEIL) });
  if (p.walkMax < WALK_CEIL) chips.push({ label: `≤ ${p.walkMax} min to ION`, clear: () => setPref("walkMax", WALK_CEIL) });
  if (p.gooseMax < 5) chips.push({ label: `geese ≤ ${p.gooseMax}`, clear: () => setPref("gooseMax", 5) });
  if (p.availableBy) chips.push({ label: `by ${p.availableBy}`, clear: () => setPref("availableBy", "") });
  if (p.triCity) chips.push({ label: "Tri-city", clear: () => setPref("triCity", false) });

  const relax = tightestFilter(p);
  const shortIds = new Set(shortlist.map((s) => s.listing.id));
  const count = results?.length ?? 0;

  return (
    <div className="page" style={{ paddingBottom: shortlist.length ? 140 : 80 }}>
      <div className="results-head">
        <div>
          <h2 className="h2">
            {results == null ? "Finding nests…" : count ? `${count} ${count === 1 ? "nest" : "nests"} worth your time` : "Nothing matched"}
            {loading && results != null && <span className="spinner" style={{ display: "inline-block", width: 18, height: 18, marginLeft: 12, verticalAlign: 2 }} />}
          </h2>
          <div className="row wrap" style={{ gap: 7, marginTop: 12 }}>
            {chips.map((c) => (
              <span className="chip" key={c.label}>
                {c.label}
                <button className="x-btn" onClick={c.clear} aria-label={`Remove filter ${c.label}`}>
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
        <div className="row wrap">
          <select className="select" value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
            <option value="best">Best match</option>
            <option value="price">Price low–high</option>
            <option value="ion">Closest to ION</option>
            <option value="geese">Fewest geese</option>
          </select>
          <div className="viewswitch" role="group" aria-label="View">
            {(["list", "split", "map"] as View[]).map((v) => (
              <button key={v} aria-pressed={view === v} onClick={() => setView(v)}>
                {v[0].toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
          <button className="btn btn-link" style={{ padding: "9px 14px", borderRadius: 10 }} onClick={() => setTuneOpen(!tuneOpen)} aria-expanded={tuneOpen}>
            Tune ranking
          </button>
        </div>
      </div>

      {tuneOpen && (
        <div className="card tune-panel" style={{ paddingTop: 4 }}>
          <WeightsPanel weights={props.weights} setWeight={props.setWeight} />
        </div>
      )}

      {error && (
        <div className="note-warn" style={{ marginTop: 18, display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
          <span className="grow">{error}</span>
          <button className="btn btn-white" onClick={props.retry}>Retry</button>
        </div>
      )}

      <div className={`split${view === "split" ? " both" : ""}`}>
        {view !== "map" && (
          <div className="list">
            {results == null && !error && [0, 1, 2].map((i) => <SkeletonCard key={i} />)}
            {sorted.map((item, i) => (
              <ListingCard
                key={item.listing.id}
                item={item}
                index={i}
                hot={hovered === item.listing.id}
                shortlisted={shortIds.has(item.listing.id)}
                onHover={() => setHovered(item.listing.id)}
                onDetail={() => props.openDetail(item)}
                onToggleShortlist={() => props.toggleShortlist(item)}
              />
            ))}
            {results != null && count === 0 && (
              <div className="empty">
                <GooseRow count={2} size={30} opacity={0.7} />
                <div className="empty-title">No nests match.</div>
                <div style={{ fontSize: 14, color: "var(--ink-2)", marginTop: 8 }}>{relax.hint}</div>
                <button className="btn-dark" style={{ marginTop: 18, cursor: "pointer" }} onClick={relax.apply(setPref)}>
                  {relax.label}
                </button>
              </div>
            )}
          </div>
        )}
        {view !== "list" && (
          <MapView
            results={sorted}
            hovered={hovered}
            onHover={(id) => {
              setHovered(id);
              if (view === "split") document.getElementById(`listing-${id}`)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
            }}
            onOpen={props.openDetail}
          />
        )}
      </div>

      {shortlist.length > 0 && (
        <div className="shortbar">
          <div className="shortbar-inner">
            <div className="row wrap" style={{ gap: 6 }}>
              {shortlist.map((s) => (
                <span className="short-chip" key={s.listing.id}>
                  {shortAddress(s.listing.address_raw)}
                </span>
              ))}
            </div>
            <div className="grow" />
            <div style={{ fontSize: 13, color: "#A39A8C" }}>Nothing is sent until you approve each message.</div>
            <button className="btn-cta" onClick={props.startContact}>
              Contact {shortlist.length} {shortlist.length === 1 ? "landlord" : "landlords"} →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="lcard" style={{ opacity: 0.7 }}>
      <div className="photo" />
      <div style={{ display: "grid", gap: 10, alignContent: "start" }}>
        <span className="skel" style={{ width: 120 }} />
        <span className="skel" style={{ width: 200, height: 20 }} />
        <span className="skel" style={{ width: 260 }} />
      </div>
      <span className="skel" style={{ width: 40, height: 24 }} />
    </div>
  );
}

/** Suggest loosening whichever filter is furthest from the default-open state. */
function tightestFilter(p: Prefs) {
  if (p.gooseMax < 5)
    return {
      hint: `Your tightest filter is geese ≤ ${p.gooseMax}. Waterloo has a lot of geese.`,
      label: `Allow up to ${Math.min(5, p.gooseMax + 2)}/5 geese`,
      apply: (set: Props["setPref"]) => () => set("gooseMax", Math.min(5, p.gooseMax + 2)),
    };
  if (p.walkMax < 20)
    return {
      hint: `Nothing within ${p.walkMax} min of the ION at this budget.`,
      label: `Allow a ${p.walkMax + 10} min walk`,
      apply: (set: Props["setPref"]) => () => set("walkMax", p.walkMax + 10),
    };
  if (p.term !== "any")
    return { hint: `Few ${p.term}-month listings match.`, label: "Any term length", apply: (set: Props["setPref"]) => () => set("term", "any") };
  return {
    hint: "Try a bigger budget or clearing a filter.",
    label: "Reset to demo defaults",
    apply: (set: Props["setPref"]) => () => (Object.keys(DEFAULT_PREFS) as (keyof Prefs)[]).forEach((k) => set(k, DEFAULT_PREFS[k] as never)),
  };
}
