import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Lang, Run } from "../api/types";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";

const MAX_IDEA_LENGTH = 500;

interface Props {
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
    return (
      <section className="card">
        <h1>Your brief</h1>
        <dl>
          <dt>Tagline</dt>
          <dd>{run.brief.tagline}</dd>
          <dt>Audience</dt>
          <dd>{run.brief.audience}</dd>
          <dt>Tone</dt>
          <dd>{run.brief.tone}</dd>
          <dt>Name ideas</dt>
          <dd>{run.brief.name_ideas.join(", ")}</dd>
        </dl>
        <button type="button" onClick={onContinue}>
          Find domains
        </button>
      </section>
    );
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <h1>What's your business idea?</h1>
      <label htmlFor="idea">Describe it in one sentence</label>
      <textarea
        id="idea"
        value={idea}
        onChange={(event) => setIdea(event.target.value)}
        maxLength={MAX_IDEA_LENGTH}
        rows={3}
        placeholder="I make homemade achaar in Lucknow and want to sell online"
        required
      />
      <label htmlFor="lang">Language</label>
      <select id="lang" value={lang} onChange={(event) => setLang(event.target.value as Lang)}>
        <option value="en">English</option>
        <option value="hi">हिन्दी</option>
      </select>
      <ErrorMessage message={error} />
      <button type="submit" disabled={loading || idea.trim() === ""}>
        {loading ? "Creating your brief…" : "Create my brief"}
      </button>
    </form>
  );
}
