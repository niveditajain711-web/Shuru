import type { Lang } from "../../api/types";
import { EXAMPLES } from "../forms/IdeaForm";

const SAMPLE_DOMAIN = "lucknowachaar.com";

interface Props {
  /** Follows the idea form's language switch, so there is only one switch on the page. */
  lang: Lang;
}

/**
 * A real Shuru site in a browser-style frame, with the idea it was made from above it.
 * The pages are static files rendered once through the real site template
 * (`backend/scripts/render_samples.py`), so showing them costs no API call.
 */
export function SampleSite({ lang }: Props) {
  return (
    <figure className="sample">
      <p className="sample-idea">
        <span className="sample-idea-label">One sentence in:</span> <q lang={lang}>{EXAMPLES[lang][0]}</q>
      </p>

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

      <figcaption className="sample-caption">A real site made by Shuru</figcaption>
    </figure>
  );
}
