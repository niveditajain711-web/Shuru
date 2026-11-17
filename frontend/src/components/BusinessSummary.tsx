import type { Run } from "../api/types";

interface Props {
  run: Run;
  /** The name idea whose domains are on screen, if the user picked one. */
  activeName?: string;
  /** Called with a name idea when the user taps it. Without it the names are plain text. */
  onPickName?: (name: string) => void;
  disabled?: boolean;
}

/** A compact reminder of the business, so the user can see their name ideas while picking a domain. */
export function BusinessSummary({ run, activeName, onPickName, disabled }: Props) {
  const { brief } = run;
  return (
    <aside className="business-summary" aria-label="Your business">
      <p className="business-tagline" lang={run.lang}>
        {brief.tagline}
      </p>

      <div>
        <p className="label" id="names-label">
          Your name ideas{onPickName && <span className="hint"> · tap one to search for it</span>}
        </p>
        <ul className="chips" aria-labelledby="names-label">
          {brief.name_ideas.map((name) => (
            <li key={name}>
              {onPickName ? (
                <button
                  type="button"
                  className="chip"
                  aria-pressed={activeName === name}
                  disabled={disabled}
                  onClick={() => onPickName(name)}
                >
                  {name}
                </button>
              ) : (
                <span className="chip">{name}</span>
              )}
            </li>
          ))}
        </ul>
      </div>

      <details>
        <summary>More about your business</summary>
        <dl className="facts">
          <div>
            <dt>Audience</dt>
            <dd lang={run.lang}>{brief.audience}</dd>
          </div>
          <div>
            <dt>Tone</dt>
            <dd lang={run.lang}>{brief.tone}</dd>
          </div>
        </dl>
      </details>
    </aside>
  );
}
