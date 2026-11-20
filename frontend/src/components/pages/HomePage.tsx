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

/** Only what the flow delivers today. Add "live on your domain" when hosting and DNS are built. */
const YOU_GET: ReactNode[] = [
  "A business summary and name ideas",
  "Available domains with real prices",
  <>
    A one-page website in English and <span lang="hi">हिन्दी</span>
  </>,
];

const PROMISES = [
  "Nothing is bought without you",
  "Prices before your site is written",
  "English and Hindi, written natively",
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
      {/* Two rows: the message centred across the page, then the form and the example as equal cards. */}
      <section className="hero" aria-labelledby="home-title">
        <div className="home-inner">
          <div className="hero-copy">
            <p className="eyebrow">
              <span lang="hi">शुरू करें</span>
              <span aria-hidden="true">·</span>
              Start your business online
            </p>
            <h1 id="home-title">
              Turn one sentence into <span className="mark">your own website</span>
            </h1>
            <p className="lead hero-lead">Shuru finds a domain name for your business and writes a one-page website for it.</p>
            <ul className="you-get" aria-label="What you get">
              {YOU_GET.map((item, index) => (
                <li key={index}>
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M5 12l5 5L19 7" />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="hero-cards">
            <IdeaForm onCreated={onCreated} />
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

          <ul className="promises" aria-label="Our promises">
            {PROMISES.map((promise) => (
              <li key={promise}>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M5 12l5 5L19 7" />
                </svg>
                {promise}
              </li>
            ))}
          </ul>

          <div className="actions home-cta">
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
