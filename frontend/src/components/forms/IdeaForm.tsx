import { useState, type FormEvent } from "react";
import { api } from "../../api/client";
import type { Lang, Run } from "../../api/types";
import { useAction } from "../../hooks/useAction";
import { ErrorMessage } from "../ui/ErrorMessage";
import { Loading } from "../ui/Loading";
import { Segmented } from "../ui/Segmented";

const MAX_IDEA_LENGTH = 500;
/** The counter shows once the text gets close to the limit; before that only screen readers hear it. */
const SHOW_COUNT_FROM = 400;

/** The textarea's id, so other parts of the page can move focus to it. */
export const IDEA_INPUT_ID = "idea";

/** The same three examples in each language, in the same order, so switching language can swap one for its twin. */
export const EXAMPLES: Record<Lang, string[]> = {
  en: [
    "I make homemade achaar in Lucknow and want to sell online",
    "I teach yoga classes online for busy office workers",
    "I run a small bakery and want customers to order cakes",
  ],
  hi: [
    "लखनऊ में घर के बने अचार का कारोबार, ऑनलाइन बिक्री के लिए",
    "व्यस्त ऑफ़िस कर्मचारियों के लिए ऑनलाइन योग कक्षाएँ",
    "एक छोटी बेकरी, जहाँ ग्राहक ऑनलाइन केक ऑर्डर कर सकें",
  ],
};

const LANGUAGES = [
  { value: "en" as const, label: "English" },
  { value: "hi" as const, label: <span lang="hi">हिन्दी</span> },
];

interface Props {
  onCreated: (run: Run) => void;
}

/**
 * The form that starts a new site: one sentence about the business, and the language of the
 * business summary. The website itself is always written in both English and Hindi.
 */
export function IdeaForm({ onCreated }: Props) {
  const [idea, setIdea] = useState("");
  const [lang, setLang] = useState<Lang>("en");
  const { run: createRun, loading, error } = useAction(api.createRun);

  // If the text is still one of the examples, switching language swaps it for the same example in the new language.
  function handleLangChange(next: Lang) {
    const index = EXAMPLES[lang].indexOf(idea);
    if (index !== -1) setIdea(EXAMPLES[next][index]);
    setLang(next);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const created = await createRun(idea.trim(), lang);
    if (created) onCreated(created);
  }

  return (
    <form className="card idea-form" onSubmit={handleSubmit} aria-label="Start a new site">
      <div className="field">
        <label htmlFor={IDEA_INPUT_ID} className="idea-label">
          What's your business idea?
        </label>
        <textarea
          id={IDEA_INPUT_ID}
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
          maxLength={MAX_IDEA_LENGTH}
          rows={3}
          lang={lang}
          placeholder={EXAMPLES[lang][0]}
          required
          disabled={loading}
          aria-describedby="idea-count"
        />
        <p
          id="idea-count"
          className={idea.length > MAX_IDEA_LENGTH - 50 ? "hint warn" : idea.length > SHOW_COUNT_FROM ? "hint" : "sr-only"}
        >
          {idea.length}/{MAX_IDEA_LENGTH}
        </p>
      </div>

      <div className="field">
        <span className="label" id="examples-label">
          Need inspiration? Try one of these
        </span>
        <ul className="chips" aria-labelledby="examples-label" lang={lang}>
          {EXAMPLES[lang].map((example) => (
            <li key={example}>
              <button type="button" className="chip" disabled={loading} onClick={() => setIdea(example)}>
                {example}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="field">
        <span className="label">Language for your summary</span>
        <Segmented label="Language for your summary" options={LANGUAGES} value={lang} onChange={handleLangChange} disabled={loading} />
        <p className="hint">
          Your website comes in both English and <span lang="hi">हिन्दी</span>. You can switch between them anytime.
        </p>
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
