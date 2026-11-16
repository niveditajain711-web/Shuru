import { useState } from "react";
import { api } from "../api/client";
import type { Lang, Run } from "../api/types";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";

interface Props {
  run: Run;
  onUpdated: (run: Run) => void;
}

const LANGUAGES: { lang: Lang; label: string }[] = [
  { lang: "en", label: "English" },
  { lang: "hi", label: "हिन्दी" },
];

export function PreviewStep({ run, onUpdated }: Props) {
  const [lang, setLang] = useState<Lang>(run.lang);
  const { run: regenerate, loading, error } = useAction(api.regenerateSite);

  async function handleRegenerate() {
    const updated = await regenerate(run.id);
    if (updated) onUpdated(updated);
  }

  return (
    <section className="card">
      <h1>Preview your site</h1>
      <p>
        Domain: <strong>{run.domain?.name}</strong>
      </p>

      <div role="group" aria-label="Language" className="toggle">
        {LANGUAGES.map((option) => (
          <button
            key={option.lang}
            type="button"
            aria-pressed={lang === option.lang}
            onClick={() => setLang(option.lang)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* The sandbox blocks scripts and navigation: the page is generated content, rendered as-is. */}
      <iframe
        className="preview"
        title="Site preview"
        sandbox=""
        src={api.previewUrl(run.id, lang, run.regenerations)}
      />

      <ErrorMessage message={error} />
      <button type="button" onClick={handleRegenerate} disabled={loading}>
        {loading ? "Writing a new version…" : "Regenerate"}
      </button>
    </section>
  );
}
