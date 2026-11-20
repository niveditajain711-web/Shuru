import { useState } from "react";
import type { Lang } from "../../api/types";
import { Segmented } from "./Segmented";

const SAMPLE_DOMAIN = "lucknowachaar.com";
const SAMPLE_IDEA = "I make homemade achaar in Lucknow and want to sell online";

const LANGUAGES = [
  { value: "en" as const, label: "English" },
  { value: "hi" as const, label: <span lang="hi">हिन्दी</span> },
];

/**
 * A real Shuru site in a browser-style frame: the sample idea above, the site it became below.
 * The pages are static files rendered once through the real site template
 * (`backend/scripts/render_samples.py`), so showing them costs no API call.
 */
export function SampleSite() {
  const [lang, setLang] = useState<Lang>("en");
  return (
    <figure className="sample">
      <p className="sample-idea">
        <span className="sample-idea-label">One sentence in</span>
        <q>{SAMPLE_IDEA}</q>
      </p>
      <span className="sample-arrow" aria-hidden="true">
        ↓
      </span>

      <div className="browser">
        <div className="browser-bar">
          <span className="browser-dots" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span className="browser-address">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <rect x="5" y="11" width="14" height="10" rx="2" />
              <path d="M8 11V7a4 4 0 0 1 8 0v4" />
            </svg>
            {SAMPLE_DOMAIN}
          </span>
        </div>
        {/* The sandbox blocks scripts and navigation, the same as the preview step. */}
        <iframe
          className="browser-frame"
          title={`Sample site for ${SAMPLE_DOMAIN} in ${lang === "en" ? "English" : "Hindi"}`}
          sandbox=""
          src={`/samples/sample-site.${lang}.html`}
        />
      </div>

      <figcaption className="sample-caption">
        <span>A website out. Made by Shuru, in both languages.</span>
        <Segmented label="Sample site language" options={LANGUAGES} value={lang} onChange={setLang} />
      </figcaption>
    </figure>
  );
}
