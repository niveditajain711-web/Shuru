import { useState, type FormEvent } from "react";
import { api } from "../../api/client";
import type { Lang, Run } from "../../api/types";
import { useAction } from "../../hooks/useAction";
import { naturalStep } from "../../lib/navigation";
import { BusinessSummary } from "../ui/BusinessSummary";
import { ErrorMessage } from "../ui/ErrorMessage";
import { Loading } from "../ui/Loading";
import { Segmented } from "../ui/Segmented";

const MAX_IDEA_LENGTH = 500;

const EXAMPLES = [
  "I make homemade achaar in Lucknow and want to sell online",
  "I teach yoga classes online for busy office workers",
  "I run a small bakery and want customers to order cakes",
];

const LANGUAGES = [
  { value: "en" as const, label: "English" },
  { value: "hi" as const, label: <span lang="hi">हिन्दी</span> },
];

interface Props {
  /** The run being viewed. Without one, this screen is the form for a new site. */
  run: Run | null;
  onCreated: (run: Run) => void;
  onContinue: () => void;
}

export function IdeaStep({ run, onCreated, onContinue }: Props) {
  const [idea, setIdea] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const { run: createRun, loading, error } = useAction(api.createRun);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const created = await createRun(idea.trim(), lang);
    if (created) onCreated(created);
  }

  if (run) {
    return <IdeaView run={run} onContinue={onContinue} />;
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h1>What's your business idea?</h1>
      <p className="lead">
        Describe it in one sentence. We'll write a short summary of your business and find domain names to match.
      </p>

      <div className="field">
        <label htmlFor="idea">Your idea</label>
        <textarea
          id="idea"
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
          maxLength={MAX_IDEA_LENGTH}
          rows={3}
          placeholder="I make homemade achaar in Lucknow and want to sell online"
          required
          disabled={loading}
          aria-describedby="idea-count"
        />
        <p id="idea-count" className={idea.length > MAX_IDEA_LENGTH - 50 ? "hint warn" : "hint"}>
          {idea.length}/{MAX_IDEA_LENGTH}
        </p>
      </div>

      <div className="field">
        <span className="label" id="examples-label">
          Need inspiration? Try one of these
        </span>
        <ul className="chips" aria-labelledby="examples-label">
          {EXAMPLES.map((example) => (
            <li key={example}>
              <button type="button" className="chip" disabled={loading} onClick={() => setIdea(example)}>
                {example}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="field">
        <span className="label">Language of your website</span>
        <Segmented label="Language of your website" options={LANGUAGES} value={lang} onChange={setLang} disabled={loading} />
      </div>

      <ErrorMessage message={error} />
      {loading ? (
        <Loading message="Creating your business summary…" />
      ) : (
        <div className="actions">
          <button type="submit" disabled={idea.trim() === ""}>
            Create my business summary
          </button>
        </div>
      )}
    </form>
  );
}

/** The idea of a run that already exists. It cannot be changed: the summary and domains were made from it. */
function IdeaView({ run, onContinue }: { run: Run; onContinue: () => void }) {
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
      <p className="hint">Website language: {run.lang === "en" ? "English" : <span lang="hi">हिन्दी</span>}</p>

      <BusinessSummary run={run} />

      <div className="actions">
        <button type="button" onClick={onContinue}>
          {continueLabel}
        </button>
      </div>
    </section>
  );
}
