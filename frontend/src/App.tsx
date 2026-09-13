import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Inquiry, Listing, ScoredListing, ScoreWeights, Source } from "@shared/types";
import { api } from "./lib/api";
import { DEFAULT_PREFS, DEFAULT_WEIGHTS, toRequirements, type Prefs } from "./lib/prefs";
import { load, save } from "./lib/storage";
import { loadRecords, saveRecords, type InquiryRecord } from "./lib/records";
import type { Sender } from "./lib/draft";
import { Header, type Screen } from "./components/Header";
import { DetailDrawer } from "./components/DetailDrawer";
import { Toast } from "./components/Toast";
import { Home, type Stats } from "./screens/Home";
import { Searching } from "./screens/Searching";
import { Results } from "./screens/Results";
import { ContactFlow } from "./screens/contact/ContactFlow";
import { Inquiries } from "./screens/Inquiries";

const MIN_SEARCH_SCREEN_MS = 1100;

const median = (xs: number[]) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

export default function App() {
  const [screen, setScreen] = useState<Screen>("home");
  const [prefs, setPrefs] = useState<Prefs>(() => ({ ...DEFAULT_PREFS, ...load<Partial<Prefs>>("prefs", {}) }));
  const [weights, setWeights] = useState<ScoreWeights>(() => ({ ...DEFAULT_WEIGHTS, ...load<Partial<ScoreWeights>>("weights", {}) }));
  const [results, setResults] = useState<ScoredListing[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [searchNonce, setSearchNonce] = useState(0);
  const [showSearchDone, setShowSearchDone] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [bySource, setBySource] = useState<Partial<Record<Source, number>>>({});
  const [shortlist, setShortlist] = useState<ScoredListing[]>([]);
  const [detail, setDetail] = useState<ScoredListing | null>(null);
  const [queue, setQueue] = useState<Listing[]>([]);
  const [resume, setResume] = useState<Inquiry | null>(null);
  const [records, setRecords] = useState<InquiryRecord[]>(loadRecords);
  const [sender, setSenderRaw] = useState<Sender>(() => load("sender", { name: "", email: "", phone: "" }));
  const [toast, setToast] = useState<string | null>(null);

  const setPref = useCallback(<K extends keyof Prefs>(k: K, v: Prefs[K]) => setPrefs((p) => ({ ...p, [k]: v })), []);
  const setWeight = useCallback((k: keyof ScoreWeights, v: number) => setWeights((w) => ({ ...w, [k]: v })), []);
  const setSender = (s: Sender) => { setSenderRaw(s); save("sender", s); };
  useEffect(() => save("prefs", prefs), [prefs]);
  useEffect(() => save("weights", weights), [weights]);
  useEffect(() => saveRecords(records), [records]);

  // Inventory stats for the hero and the searching screen.
  useEffect(() => {
    api.listings(1000).then((ls) => {
      const counts: Partial<Record<Source, number>> = {};
      ls.forEach((l) => (counts[l.source] = (counts[l.source] ?? 0) + 1));
      setBySource(counts);
      setStats({
        total: ls.length,
        medianPrice: median(ls.map((l) => l.price_min).filter((p): p is number => p != null)),
        medianWalk: median(ls.map((l) => l.ion_walk_min).filter((p): p is number => p != null)),
        medianGeese: median(ls.map((l) => l.geese_score).filter((g): g is number => g != null)),
      });
    }).catch(() => {});
  }, []);

  // Live search: re-rank whenever filters or weights change (debounced).
  const reqKey = JSON.stringify(toRequirements(prefs, weights));
  const pendingSearch = useRef<Promise<void> | null>(null);
  useEffect(() => {
    const ctl = new AbortController();
    setSearching(true);
    const t = setTimeout(() => {
      pendingSearch.current = api
        .search(JSON.parse(reqKey), ctl.signal)
        .then((r) => { setResults(r); setSearchError(null); })
        .catch((e) => { if (!ctl.signal.aborted) setSearchError(e.message); })
        .finally(() => { if (!ctl.signal.aborted) setSearching(false); });
    }, 250);
    return () => { clearTimeout(t); ctl.abort(); };
  }, [reqKey, searchNonce]);

  const runSearch = async () => {
    setScreen("searching");
    setShowSearchDone(false);
    const started = Date.now();
    await new Promise((r) => setTimeout(r, 300)); // let the debounced request fire
    await pendingSearch.current?.catch(() => {});
    setShowSearchDone(true);
    await new Promise((r) => setTimeout(r, Math.max(250, MIN_SEARCH_SCREEN_MS - (Date.now() - started))));
    setScreen("results");
  };

  const toggleShortlist = (item: ScoredListing) =>
    setShortlist((s) => (s.some((x) => x.listing.id === item.listing.id) ? s.filter((x) => x.listing.id !== item.listing.id) : [...s, item]));

  const upsertInquiry = useCallback((inquiry: Inquiry, listing: Listing) => {
    setRecords((rs) => {
      const i = rs.findIndex((r) => r.inquiry.id === inquiry.id);
      if (i === -1) return [{ inquiry, listing }, ...rs];
      const next = [...rs];
      next[i] = { inquiry, listing };
      return next;
    });
  }, []);

  const needsAttention = records.filter((r) => r.inquiry.status === "pending_approval").length;
  const shortIds = useMemo(() => new Set(shortlist.map((s) => s.listing.id)), [shortlist]);

  const go = (s: Screen) => { setDetail(null); setScreen(s); window.scrollTo({ top: 0 }); };

  return (
    <>
      <Header
        screen={screen}
        shortlistCount={shortlist.length}
        inquiryCount={records.length}
        needsAttention={needsAttention}
        hasResults={results != null}
        go={go}
      />

      {screen === "home" && (
        <Home
          prefs={prefs}
          setPref={setPref}
          weights={weights}
          setWeight={setWeight}
          matchCount={searching ? null : results?.length ?? null}
          stats={stats}
          apiError={searchError}
          onSearch={runSearch}
        />
      )}

      {screen === "searching" && <Searching bySource={bySource} done={showSearchDone} />}

      {screen === "results" && (
        <Results
          results={results}
          loading={searching}
          error={searchError}
          prefs={prefs}
          setPref={setPref}
          weights={weights}
          setWeight={setWeight}
          shortlist={shortlist}
          toggleShortlist={toggleShortlist}
          openDetail={setDetail}
          startContact={() => { setQueue(shortlist.map((s) => s.listing)); setResume(null); go("contact"); }}
          retry={() => setSearchNonce((n) => n + 1)}
        />
      )}

      {screen === "contact" && queue.length > 0 && (
        <ContactFlow
          key={resume?.id ?? queue.map((l) => l.id).join()}
          queue={queue}
          resume={resume}
          sender={sender}
          setSender={setSender}
          onInquiry={upsertInquiry}
          onBack={() => go(results ? "results" : "home")}
          onInquiries={() => go("inquiries")}
          onQueueDone={() => { setShortlist([]); go(results ? "results" : "home"); }}
          toast={setToast}
        />
      )}

      {screen === "inquiries" && (
        <Inquiries
          records={records}
          goHome={() => go("home")}
          open={(r) => { setQueue([r.listing]); setResume(r.inquiry); go("contact"); }}
        />
      )}

      {detail && (
        <DetailDrawer
          item={detail}
          shortlisted={shortIds.has(detail.listing.id)}
          onClose={() => setDetail(null)}
          onToggleShortlist={() => toggleShortlist(detail)}
        />
      )}

      {toast && <Toast message={toast} onClose={() => setToast(null)} />}
    </>
  );
}
