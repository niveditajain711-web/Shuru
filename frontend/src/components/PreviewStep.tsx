import { useState } from "react";
import { api } from "../api/client";
import type { Lang, Run } from "../api/types";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";
import { Loading } from "./Loading";
import { Segmented } from "./Segmented";

// Mirrors the backend's default regeneration cap (SHURU_REGENERATION_CAP). If it is configured
// differently, the backend's own error message still explains the limit.
const REGENERATION_CAP = 3;

const LANGUAGES = [
  { value: "en" as const, label: "English" },
  { value: "hi" as const, label: <span lang="hi">हिन्दी</span> },
];

interface Props {
  run: Run;
  onUpdated: (run: Run) => void;
  onStartOver: () => void;
}

export function PreviewStep({ run, onUpdated, onStartOver }: Props) {
  const [lang, setLang] = useState<Lang>(run.lang);
  const { run: regenerate, loading, error } = useAction(api.regenerateSite);
  const left = Math.max(REGENERATION_CAP - run.regenerations, 0);

  async function handleRegenerate() {
    const updated = await regenerate(run.id);
    if (updated) onUpdated(updated);
  }

  return (
    <section className="card">
      <h1>Preview your site</h1>
      <p className="lead">
        This is how your site for <strong>{run.domain?.name}</strong> will look. Switch language to check both versions.
      </p>

      <Segmented label="Preview language" options={LANGUAGES} value={lang} onChange={setLang} />

      {/* The sandbox blocks scripts and navigation: the page is generated content, rendered as-is. */}
      <iframe
        className="preview"
        title={`Site preview in ${lang === "en" ? "English" : "Hindi"}`}
        sandbox=""
        src={api.previewUrl(run.id, lang, run.regenerations)}
      />

      <ErrorMessage message={error} />
      {loading ? (
        <Loading message="Writing a new version…" detail="This takes about 20 seconds." />
      ) : (
        <div className="actions">
          <button type="button" className="secondary" onClick={handleRegenerate} disabled={left === 0}>
            {left === 0 ? "No regenerations left" : `Regenerate (${left} of ${REGENERATION_CAP} left)`}
          </button>
        </div>
      )}

      <div className="next-panel">
        <h2>What's next</h2>
        <p>Next you'll be able to buy your domain and put this site live. That step is coming soon.</p>
        <div className="actions">
          <button type="button" disabled>
            Buy domain (coming soon)
          </button>
          <button type="button" className="secondary" onClick={onStartOver}>
            Start over
          </button>
        </div>
      </div>
    </section>
  );
}
