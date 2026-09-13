import { useState } from "react";
import type { ScoredListing } from "@shared/types";
import { availableLine, cleanAddress, gooseWord, ionLine, priceLabel, termLine, unitLine } from "../lib/format";
import { GooseDots, Photo } from "./Goose";
import { KindBadge, SourceBadges } from "./Badges";
import { ScoreBreakdown, topReasons } from "./ScoreBreakdown";

interface Props {
  item: ScoredListing;
  index: number;
  hot: boolean;
  shortlisted: boolean;
  onHover: () => void;
  onDetail: () => void;
  onToggleShortlist: () => void;
}

/** Enrichment may still be null; show a shimmer, never "0 min". */
const Skel = () => <span className="skel" aria-label="loading" />;

export function ListingCard({ item, index, hot, shortlisted, onHover, onDetail, onToggleShortlist }: Props) {
  const [open, setOpen] = useState(false);
  const l = item.listing;
  const canAuto = l.contact_method === "form" || l.contact_method === "email" || l.contact_method === "phone";
  const term = termLine(l);
  const avail = availableLine(l.available_date);
  const ion = ionLine(l);

  return (
    <article
      className={`lcard${hot ? " hot" : ""}`}
      style={{ animationDelay: `${Math.min(index, 12) * 0.05}s` }}
      onMouseEnter={onHover}
      id={`listing-${l.id}`}
    >
      <Photo src={l.image_url} label="no photo · goose placeholder" />

      <div style={{ minWidth: 0 }}>
        <div className="row wrap" style={{ gap: 7 }}>
          <KindBadge kind={l.listing_kind} />
          <SourceBadges source={l.source} also={item.also_listed_on} />
        </div>
        <div className="row wrap" style={{ alignItems: "baseline", gap: 10, marginTop: 9 }}>
          <span className="price">{priceLabel(l)}</span>
          <span style={{ fontSize: 15, color: "var(--ink-2)" }}>{unitLine(l)}</span>
        </div>
        <div style={{ fontSize: 14, color: "var(--ink-2)", marginTop: 4 }}>{cleanAddress(l.address_raw)}</div>
        <div className="facts">
          {term && <span className="fact">{term}</span>}
          {avail && <span className="fact">{avail}</span>}
          <span className="fact">{ion ?? <Skel />}</span>
          <span className="fact">
            {l.geese_score == null ? (
              <Skel />
            ) : (
              <>
                <GooseDots score={l.geese_score} />
                {gooseWord(l.geese_score)}
              </>
            )}
          </span>
        </div>
        <div className="reasons">
          {topReasons(item.breakdown).map((r) => (
            <span key={r} className="reason">
              {r}
            </span>
          ))}
        </div>
        <button className="link-btn" style={{ marginTop: 12 }} onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "Hide score breakdown" : "Why this score?"}
        </button>
        {open && (
          <div className="breakdown">
            <ScoreBreakdown factors={item.breakdown} />
          </div>
        )}
      </div>

      <div className="card-side" style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", justifyContent: "space-between", gap: 14 }}>
        <div className="score">
          <b>{Math.round(item.score)}</b>
          <small>match</small>
          <div className="score-track">
            <div style={{ width: `${Math.min(100, item.score)}%` }} />
          </div>
        </div>
        <div className="card-actions">
          <button className="btn" onClick={onDetail}>
            Details
          </button>
          <button
            className={`btn-short${canAuto ? "" : " nope"}`}
            aria-pressed={shortlisted}
            onClick={onToggleShortlist}
          >
            {shortlisted ? "✓ Shortlisted" : canAuto ? "Contact" : "Shortlist"}
          </button>
          {!canAuto && !shortlisted && (
            <span style={{ fontSize: 11, color: "var(--ink-4)", textAlign: "center" }}>login required</span>
          )}
        </div>
      </div>
    </article>
  );
}
