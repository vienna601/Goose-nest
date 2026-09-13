import { useMemo } from "react";
import type { ScoredListing } from "@shared/types";
import { money } from "../lib/format";

// ION stops, same coordinates as backend/services/enrich.py.
export const ION_STOPS: [string, number, number][] = [
  ["Conestoga", 43.49821, -80.52953],
  ["Northfield", 43.49736, -80.5433],
  ["Research & Technology", 43.48136, -80.54527],
  ["University of Waterloo", 43.47229, -80.54486],
  ["Laurier–Waterloo Park", 43.46899, -80.5345],
  ["Waterloo Public Square", 43.46414, -80.52289],
  ["Willis Way", 43.46228, -80.52354],
  ["Allen", 43.46015, -80.51886],
  ["Grand River Hospital", 43.4573, -80.51217],
  ["Central Station", 43.45333, -80.49944],
  ["Kitchener City Hall", 43.45202, -80.49104],
  ["Victoria Park", 43.45016, -80.49354],
  ["Queen", 43.44871, -80.48966],
  ["Frederick", 43.44938, -80.48748],
  ["Kitchener Market", 43.44639, -80.48361],
  ["Borden", 43.44228, -80.47501],
  ["Mill", 43.43395, -80.47839],
  ["Block Line", 43.41902, -80.4666],
  ["Fairway", 43.42235, -80.44179],
];

/** Deterministic pseudo-random in [0,1) so blobs don't jump between renders. */
const rand = (i: number, m: number) => ((i * 9301 + 49297) % m) / m;

interface Props {
  results: ScoredListing[];
  hovered: string | null;
  onHover: (id: string) => void;
  onOpen: (item: ScoredListing) => void;
}

export function MapView({ results, hovered, onHover, onOpen }: Props) {
  const placed = results.filter((r) => r.listing.lat != null && r.listing.lng != null);

  // Fit the frame to the results with a minimum span (~3 km), centred on them;
  // defaults to uptown Waterloo when there's nothing to show.
  const project = useMemo(() => {
    const lats = placed.length ? placed.map((r) => r.listing.lat!) : [43.4643];
    const lngs = placed.length ? placed.map((r) => r.listing.lng!) : [-80.5204];
    const cLat = (Math.min(...lats) + Math.max(...lats)) / 2;
    const cLng = (Math.min(...lngs) + Math.max(...lngs)) / 2;
    const halfLat = Math.max(0.014, ((Math.max(...lats) - Math.min(...lats)) / 2) * 1.2);
    const halfLng = Math.max(0.02, ((Math.max(...lngs) - Math.min(...lngs)) / 2) * 1.25);
    const minLat = cLat - halfLat, maxLat = cLat + halfLat;
    const minLng = cLng - halfLng, maxLng = cLng + halfLng;
    return (lat: number, lng: number) => ({
      x: ((lng - minLng) / (maxLng - minLng)) * 100,
      y: ((maxLat - lat) / (maxLat - minLat)) * 100,
    });
  }, [placed]);

  const stops = ION_STOPS.map(([name, lat, lng]) => ({ name, ...project(lat, lng) }));
  const inFrame = stops.filter((s) => s.x > 2 && s.x < 98 && s.y > 2 && s.y < 98);

  const blobs = placed.flatMap((r, i) =>
    Array.from({ length: (r.listing.geese_score ?? 1) * 3 - 2 }, (_, k) => {
      const p = project(
        r.listing.lat! + (rand(i * 7 + k, 13) - 0.5) * 0.006,
        r.listing.lng! + (rand(i * 5 + k + 2, 11) - 0.5) * 0.008,
      );
      return { key: `${r.listing.id}-${k}`, ...p, size: 8 + rand(k + i, 7) * 16, dur: 2.2 + rand(k, 9) * 3, delay: rand(k + 4, 11) * 2.6 };
    }),
  );

  return (
    <div className="map-wrap">
      <div className="map" role="region" aria-label="Map of results">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <polyline
            points={stops.map((s) => `${s.x},${s.y}`).join(" ")}
            fill="none"
            stroke="#8A7060"
            strokeWidth="3"
            strokeLinejoin="round"
            opacity="0.55"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        {blobs.map((b) => (
          <span
            key={b.key}
            className="goose-blob"
            style={{ left: `${b.x}%`, top: `${b.y}%`, width: b.size, height: b.size, animation: `gnPulse ${b.dur.toFixed(1)}s infinite ${b.delay.toFixed(1)}s` }}
          />
        ))}
        {inFrame.map((s) => {
          const flip = s.x > 52;
          return (
            <div
              key={s.name}
              className="stop"
              style={{ left: `${s.x}%`, top: `${s.y}%`, transform: `translate(${flip ? "-100%" : "0"}, -50%)`, flexDirection: flip ? "row-reverse" : "row" }}
            >
              <i />
              <span>{s.name}</span>
            </div>
          );
        })}
        {placed.map((r, i) => {
          const p = project(r.listing.lat!, r.listing.lng!);
          const on = hovered === r.listing.id;
          const price = r.listing.price_min ?? r.listing.price_max;
          return (
            <button
              key={r.listing.id}
              className={`pin${on ? " hot" : ""}`}
              style={{ left: `${p.x}%`, top: `${p.y}%`, zIndex: on ? 9 : 5 }}
              onMouseEnter={() => onHover(r.listing.id)}
              onFocus={() => onHover(r.listing.id)}
              onClick={() => onOpen(r)}
              aria-label={`${price ? money(price) : "listing"} at ${r.listing.address_raw}`}
            >
              <span style={{ animationDelay: `${Math.min(i, 20) * 0.05}s` }}>{price ? money(price) : "?"}</span>
            </button>
          );
        })}
        <div className="legend">
          <div className="row" style={{ gap: 7 }}>
            <span style={{ width: 10, height: 2, background: "#8A7060" }} />
            ION light rail
          </div>
          <div className="row" style={{ gap: 7 }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#9C6B3F", opacity: 0.4 }} />
            goose activity near listings (iNaturalist)
          </div>
        </div>
      </div>
    </div>
  );
}
