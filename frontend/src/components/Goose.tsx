import type { CSSProperties } from "react";

export const GOOSE_PATH =
  "M1.9 8.2c0-1.7 1.5-2.6 3.3-2.6.7 0 1.3.1 1.8.4V3.2c0-1 .7-1.7 1.6-1.7.8 0 1.5.6 1.5 1.4v.3l1.6.6-1.6.6c-.1.9-.4 1.4-.8 2-.7 1.1-.5 2-1.5 2.9-.8.8-2 1.2-3.3 1.2-1.7 0-2.6-.9-2.6-2.3z";

export function Goose({ size = 16, fill = "#8A7060", style }: { size?: number; fill?: string; style?: CSSProperties }) {
  return (
    <svg viewBox="0 0 12 12" width={size} height={size} style={style} aria-hidden="true">
      <path d={GOOSE_PATH} fill={fill} />
    </svg>
  );
}

/** Row of goose silhouettes — the no-photo placeholder and empty-state art. */
export function GooseRow({ count = 3, size = 16, opacity = 0.6 }: { count?: number; size?: number; opacity?: number }) {
  return (
    <div style={{ display: "flex", gap: size * 0.45, opacity, justifyContent: "center" }}>
      {Array.from({ length: count }, (_, i) => (
        <Goose key={i} size={size} />
      ))}
    </div>
  );
}

/** 1–5 dots. 1 = no geese (good), 5 = hellscape (bad); heavier = warmer brown. */
export function GooseDots({ score, size = 7, dark = false }: { score: number; size?: number; dark?: boolean }) {
  const on = dark ? "#9C6B3F" : score >= 4 ? "#7A4E2B" : score === 3 ? "#A9763F" : "#8A7060";
  const off = dark ? "#4A453D" : "#DFD6C5";
  return (
    <span style={{ display: "inline-flex", gap: size * 0.8 }} role="img" aria-label={`goose score ${score} of 5`}>
      {Array.from({ length: 5 }, (_, i) => (
        <span key={i} style={{ width: size, height: size, borderRadius: "50%", background: i < score ? on : off }} />
      ))}
    </span>
  );
}

export function Photo({ src, label, height, goose = 3 }: { src: string | null; label?: string; height?: number; goose?: number }) {
  return (
    <div className="photo" style={height ? { height } : undefined}>
      <GooseRow count={goose} />
      {src && (
        <img
          src={src}
          alt=""
          loading="lazy"
          onError={(e) => ((e.currentTarget as HTMLImageElement).style.display = "none")}
        />
      )}
      {!src && label && <div className="photo-label">{label}</div>}
    </div>
  );
}
