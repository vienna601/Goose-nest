import { useEffect } from "react";
import type { ScoredListing } from "@shared/types";
import {
  availableLine, bedsLabel, cleanAddress, contactMethodLabel, dist, gooseWord, priceLabel, sourceLabel, termLine, unitLine,
} from "../lib/format";
import { Goose, GooseDots, GooseRow } from "./Goose";
import { KindBadge, SourceBadges } from "./Badges";
import { ScoreBreakdown } from "./ScoreBreakdown";

interface Props {
  item: ScoredListing;
  shortlisted: boolean;
  onClose: () => void;
  onToggleShortlist: () => void;
}

const rand = (i: number, m: number) => ((i * 9301 + 49297) % m) / m;

export function DetailDrawer({ item, shortlisted, onClose, onToggleShortlist }: Props) {
  const l = item.listing;
  const images = l.images.length ? l.images : l.image_url ? [l.image_url] : [];

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const na = <span className="muted">—</span>;
  const beds = bedsLabel(l.beds, l.den);
  const facts = [termLine(l), availableLine(l.available_date)].filter(Boolean).join(" · ");

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Details for ${l.address_raw}`}>
        <div className="drawer-inner">
          <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
            <div>
              <div className="row wrap" style={{ gap: 7 }}>
                <KindBadge kind={l.listing_kind} />
                <SourceBadges source={l.source} also={item.also_listed_on} />
              </div>
              <div style={{ fontFamily: "var(--display)", fontWeight: 800, fontSize: 30, letterSpacing: "-.03em", marginTop: 10 }}>
                {priceLabel(l)}
              </div>
              <div style={{ fontSize: 15, color: "var(--ink-2)" }}>
                {unitLine(l)} · {cleanAddress(l.address_raw)}
              </div>
              {facts && <div style={{ fontSize: 13.5, color: "var(--ink-3)", marginTop: 4 }}>{facts}</div>}
            </div>
            <button className="close-btn" onClick={onClose} aria-label="Close">
              ×
            </button>
          </div>

          <div className="gallery">
            {images.length ? (
              images.map((src, i) => <img key={src + i} src={src} alt={`Photo ${i + 1} of ${images.length}`} loading="lazy" />)
            ) : (
              <div>
                <GooseRow count={4} size={26} opacity={0.55} />
              </div>
            )}
          </div>
          {images.length > 1 && <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{images.length} photos · scroll sideways</div>}

          <div className="card-sm" style={{ marginTop: 20 }}>
            <div className="eyebrow">Why it ranks {Math.round(item.score)}</div>
            <div style={{ marginTop: 12 }}>
              <ScoreBreakdown factors={item.breakdown} />
            </div>
          </div>

          <div className="two-col" style={{ marginTop: 14 }}>
            <div className="card-sm">
              <div className="eyebrow">Neighbourhood</div>
              <div style={{ marginTop: 12, display: "grid", gap: 9 }}>
                <div className="kv"><span>Nearest ION</span><span style={{ textAlign: "right" }}>{l.nearest_ion_stop ?? na}</span></div>
                <div className="kv"><span>Walk</span><span className="mono">{l.ion_walk_min != null ? `${l.ion_walk_min} min · ${dist(l.ion_distance_m)}` : na}</span></div>
                <div className="kv"><span>GO station</span><span className="mono">{dist(l.go_distance_m) ?? na}</span></div>
                <div className="kv"><span>Highway</span><span className="mono">{dist(l.highway_distance_m) ?? na}</span></div>
                <div className="kv"><span>Beds / baths</span><span className="mono">{beds ?? "—"} / {l.baths != null ? `${l.baths} bath` : "—"}</span></div>
              </div>
            </div>
            <div className="geese-card">
              {Array.from({ length: (l.geese_score ?? 1) * 2 }, (_, i) => (
                <span
                  key={i}
                  style={{
                    position: "absolute", top: `${(rand(i + 1, 13) * 90).toFixed(0)}%`, left: `${(rand(i + 4, 17) * 88).toFixed(0)}%`,
                    opacity: 0.25, animation: `gnPulse ${(2.4 + rand(i + 2, 7) * 3).toFixed(1)}s infinite ${(rand(i + 6, 11) * 2.2).toFixed(1)}s`,
                  }}
                >
                  <Goose size={10 + rand(i, 5) * 14} fill="#9C6B3F" />
                </span>
              ))}
              <div style={{ position: "relative" }}>
                <div className="eyebrow" style={{ color: "var(--ink-4)" }}>Geese</div>
                {l.geese_score == null ? (
                  <div style={{ fontSize: 14, color: "#DCD5C8", marginTop: 8 }}>Still counting…</div>
                ) : (
                  <>
                    <div style={{ fontFamily: "var(--display)", fontWeight: 800, fontSize: 30, letterSpacing: "-.03em", marginTop: 8 }}>
                      {l.geese_score} / 5
                    </div>
                    <div style={{ fontSize: 14, color: "#DCD5C8" }}>{l.geese_zone ?? gooseWord(l.geese_score)}</div>
                    <div style={{ marginTop: 12 }}>
                      <GooseDots score={l.geese_score} size={10} dark />
                    </div>
                  </>
                )}
                <div style={{ fontSize: 11.5, lineHeight: 1.5, color: "#A39A8C", marginTop: 12 }}>
                  Based on research-grade Canada Goose sightings from iNaturalist within 500 m. 1 = no geese, 5 = goose hellscape.
                </div>
              </div>
            </div>
          </div>

          <div className="note-warn" style={{ marginTop: 14 }}>
            Student housing has a lot of scams. Never e-transfer a deposit before you've seen the unit or met the landlord.
            Goose Nest never asks for money.
          </div>

          <div className="row wrap" style={{ marginTop: 18, gap: 10 }}>
            <button className="btn-cta" onClick={onToggleShortlist}>
              {shortlisted ? "✓ On your shortlist" : "Contact this landlord"}
            </button>
            <a href={l.url} target="_blank" rel="noreferrer" style={{ fontSize: 13.5 }}>
              View on {sourceLabel(l.source)} ↗
            </a>
          </div>
          <div style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 10 }}>
            Contact: {l.contact_name ?? "landlord"} · {contactMethodLabel(l.contact_method)}
            {l.contact_behind_click && " · behind a “show contact” click on the source site"}
          </div>
        </div>
      </aside>
    </>
  );
}
