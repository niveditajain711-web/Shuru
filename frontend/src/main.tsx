import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";
import "./styles/styles.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root element #root not found");
}

// StrictMode is left off on purpose: its dev-only double effects would start every domain
// search twice, and each search runs several external calls.
createRoot(container).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>,
);
