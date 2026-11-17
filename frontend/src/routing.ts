import { useMemo, useSyncExternalStore } from "react";
import { parseRoute, routeHash, type Route, type Step } from "./navigation";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

/** The current route, read from the URL hash. Works with refresh and the browser Back button. */
export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash);
  return useMemo(() => parseRoute(hash), [hash]);
}

/** Go to a step. `replace` fixes the current history entry instead of adding one. */
export function navigate(runId: string | null, step: Step, replace = false): void {
  const hash = routeHash(runId, step);
  if (window.location.hash === hash) return;
  if (replace) {
    window.location.replace(hash);
  } else {
    window.location.hash = hash;
  }
}
