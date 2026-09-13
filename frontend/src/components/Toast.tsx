import { useEffect } from "react";

export function Toast({ message, onClose }: { message: string; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 6000);
    return () => clearTimeout(t);
  }, [message, onClose]);
  return (
    <div className="toast" role="alert">
      <span>{message}</span>
      <button className="x-btn" style={{ background: "#3B3831", color: "#CFC7B8" }} onClick={onClose} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
