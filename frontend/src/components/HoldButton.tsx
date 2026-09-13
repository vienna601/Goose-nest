import { useEffect, useRef, useState } from "react";

/** Approve must be deliberate: press and hold (mouse, touch, Space or Enter)
 *  for `ms`. Releasing early resets. */
export function HoldButton({ ms = 1200, disabled, onConfirm, label, holdingLabel }: {
  ms?: number;
  disabled?: boolean;
  onConfirm: () => void;
  label: string;
  holdingLabel: string;
}) {
  const [pct, setPct] = useState(0);
  const raf = useRef<number>();
  const start = useRef<number>();
  const fired = useRef(false);

  const stop = () => {
    if (raf.current) cancelAnimationFrame(raf.current);
    raf.current = undefined;
    start.current = undefined;
    if (!fired.current) setPct(0);
  };

  const begin = () => {
    if (disabled || raf.current || fired.current) return;
    const tick = (t: number) => {
      start.current ??= t;
      const p = Math.min(100, ((t - start.current) / ms) * 100);
      setPct(p);
      if (p >= 100) {
        fired.current = true;
        raf.current = undefined;
        onConfirm();
      } else {
        raf.current = requestAnimationFrame(tick);
      }
    };
    raf.current = requestAnimationFrame(tick);
  };

  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current); }, []);
  useEffect(() => { if (!disabled) { fired.current = false; setPct(0); } }, [disabled]);

  return (
    <button
      className="hold"
      disabled={disabled}
      onPointerDown={begin}
      onPointerUp={stop}
      onPointerLeave={stop}
      onPointerCancel={stop}
      onKeyDown={(e) => { if ((e.key === " " || e.key === "Enter") && !e.repeat) { e.preventDefault(); begin(); } }}
      onKeyUp={(e) => { if (e.key === " " || e.key === "Enter") stop(); }}
      onContextMenu={(e) => e.preventDefault()}
      aria-label={`${label} (press and hold)`}
    >
      <span className="fill" style={{ width: `${pct}%` }} />
      <span className="lbl">{pct > 0 && pct < 100 ? holdingLabel : label}</span>
    </button>
  );
}
