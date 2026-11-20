import type { ReactNode } from "react";
import type { Run } from "../../api/types";
import { IDEA_INPUT_ID, IdeaForm } from "../forms/IdeaForm";
import { SampleSite } from "../ui/SampleSite";

interface Props {
  onCreated: (run: Run) => void;
  onSupport: () => void;
}

const HOW_IT_WORKS: { title: string; text: ReactNode }[] = [
  { title: "Describe your idea", text: "One sentence is enough. We write a short summary and name ideas." },
  { title: "Pick a domain", text: "Choose from available names with real first-year and renewal prices." },
  {
    title: "Preview your site",
    text: (
      <>
        A one-page website in English and <span lang="hi">हिन्दी</span>. Not happy? Write it again.
      </>
    ),
  },
  { title: "Buy when you're ready", text: "You see the final price and agree to the terms before anything is bought." },
];

const PROMISES: { title: string; text: string; icon: ReactNode }[] = [
  {
    title: "Nothing is bought without you",
    text: "Every step that costs money waits for your approval.",
    icon: <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z M9 12l2 2 4-4" />,
  },
  {
    title: "Prices up front",
    text: "You see the domain price and renewal price before your site is written.",
    icon: <path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9-9-9z M8 8h.01" />,
  },
  {
    title: "Written in your language",
    text: "English and Hindi are each written natively, not machine-translated.",
    icon: <path d="M4 5h9 M8.5 3v2 M6 5c1 4 4 7 7 8 M11 5c-1 4-4 7-7 8 M13 21l4-10 4 10 M14.5 17h5" />,
  },
];

/** Move to the idea form: scroll it into view and put the cursor in the text box. */
function focusIdeaForm() {
  const input = document.getElementById(IDEA_INPUT_ID);
  if (!input) return;
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  input.scrollIntoView?.({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
  input.focus({ preventScroll: true });
}

/** The first screen: what Shuru does, the form to start, and a real sample of the result. */
export function HomePage({ onCreated, onSupport }: Props) {
  return (
    <div className="home">
      <section className="hero" aria-labelledby="home-title">
        <div className="home-inner hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">
              <span lang="hi">शुरू करें</span>
              <span aria-hidden="true">·</span>
              Start your business online
            </p>
            <h1 id="home-title">
              Turn one sentence into <span className="mark">your own website</span>
            </h1>
            <p className="lead hero-lead">
              Shuru finds a domain name for your business and writes a one-page website for it, in English or Hindi. You
              approve every step.
            </p>
            <IdeaForm onCreated={onCreated} />
          </div>
          <div className="hero-visual">
            <SampleSite />
          </div>
        </div>
      </section>

      <section className="home-section" aria-labelledby="how-title">
        <div className="home-inner">
          <h2 id="how-title" className="section-title">
            How it works
          </h2>
          <ol className="how-steps">
            {HOW_IT_WORKS.map(({ title, text }, index) => (
              <li key={title} className="how-step">
                <span className="how-marker" aria-hidden="true">
                  {index + 1}
                </span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="home-section home-section-tinted" aria-labelledby="promise-title">
        <div className="home-inner">
          <h2 id="promise-title" className="section-title">
            Made for first-time founders
          </h2>
          <ul className="promises">
            {PROMISES.map(({ title, text, icon }) => (
              <li key={title} className="promise">
                <span className="promise-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    {icon}
                  </svg>
                </span>
                <h3>{title}</h3>
                <p>{text}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="home-section home-cta" aria-labelledby="cta-title">
        <div className="home-inner">
          <h2 id="cta-title" className="section-title">
            Your business deserves a home online
          </h2>
          <p className="lead">It starts with one sentence.</p>
          <div className="actions">
            <button type="button" onClick={focusIdeaForm}>
              Start my site
            </button>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div className="home-inner">
          <span>
            © {new Date().getFullYear()} Shuru · <span lang="hi">शुरू</span>
          </span>
          <button type="button" className="link" onClick={onSupport}>
            Need help? Contact support
          </button>
        </div>
      </footer>
    </div>
  );
}
