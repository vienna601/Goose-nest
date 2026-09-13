// localStorage wrappers. Every access can throw (private mode, blocked site
// data), and the app must still work with nothing stored.
export function load<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem("goose-nest:" + key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function save(key: string, value: unknown) {
  try {
    localStorage.setItem("goose-nest:" + key, JSON.stringify(value));
  } catch {
    /* not fatal */
  }
}
