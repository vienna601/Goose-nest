import { Goose } from "./Goose";

export type Screen = "home" | "searching" | "results" | "contact" | "inquiries";

interface Props {
  screen: Screen;
  shortlistCount: number;
  inquiryCount: number;
  needsAttention: number;
  hasResults: boolean;
  go: (s: Screen) => void;
}

export function Header({ screen, shortlistCount, inquiryCount, needsAttention, hasResults, go }: Props) {
  const tabs: { label: string; target: Screen; current: boolean; count: number; attention?: boolean }[] = [
    { label: "Search", target: "home", current: screen === "home" || screen === "searching", count: 0 },
    { label: "Shortlist", target: hasResults ? "results" : "home", current: screen === "results" || screen === "contact", count: shortlistCount },
    { label: "My inquiries", target: "inquiries", current: screen === "inquiries", count: needsAttention || inquiryCount, attention: needsAttention > 0 },
  ];
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <button className="brand" onClick={() => go("home")} aria-label="Goose Nest home">
          <span className="brand-mark">
            <Goose size={19} fill="#FFD100" />
          </span>
          <span className="brand-word">Goose&nbsp;Nest</span>
        </button>
        <nav className="row" style={{ gap: 4 }}>
          {tabs.map((t) => (
            <button key={t.label} className="nav-tab" aria-current={t.current ? "page" : undefined} onClick={() => go(t.target)}>
              <span className="nav-dot" />
              <span className="nav-label">{t.label}</span>
              {t.count > 0 && <span className={`nav-count${t.attention ? " attention" : ""}`}>{t.count}</span>}
            </button>
          ))}
        </nav>
        <div className="grow" />
        <div className="steel-tag">
          <span className="live-dot" />
          Agent runs on Steel
        </div>
      </div>
    </header>
  );
}
