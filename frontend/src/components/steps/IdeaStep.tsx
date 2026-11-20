import type { Run } from "../../api/types";
import { naturalStep } from "../../lib/navigation";
import { BusinessSummary } from "../ui/BusinessSummary";

interface Props {
  run: Run;
  onContinue: () => void;
}

/**
 * The idea of a run that already exists. It cannot be changed: the summary and domains were made
 * from it. New sites start from the form on the homepage.
 */
export function IdeaStep({ run, onContinue }: Props) {
  const continueLabel = {
    idea: "Continue",
    domain: "Back to domains",
    review: "Back to the price",
    preview: "Back to your site",
    checkout: "Continue",
  }[naturalStep(run)];
  return (
    <section className="card">
      <h1>Your idea</h1>
      <p className="lead">Your idea is saved. To change it, start a new site.</p>

      <blockquote className="tagline" lang={run.lang}>
        {run.idea}
      </blockquote>
      <p className="hint">
        Summary language: {run.lang === "en" ? "English" : <span lang="hi">हिन्दी</span>}. Your website comes in both
        English and <span lang="hi">हिन्दी</span>.
      </p>

      <BusinessSummary run={run} />

      <div className="actions">
        <button type="button" onClick={onContinue}>
          {continueLabel}
        </button>
      </div>
    </section>
  );
}
