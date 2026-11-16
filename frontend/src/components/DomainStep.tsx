import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { DomainOffer, Run } from "../api/types";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";

interface Props {
  run: Run;
  onChosen: (run: Run) => void;
}

function formatPrice({ price, currency }: DomainOffer): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(price);
}

export function DomainStep({ run, onChosen }: Props) {
  const [domains, setDomains] = useState<DomainOffer[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [keyword, setKeyword] = useState("");
  const { run: search, loading: searching, error: searchError } = useAction(api.listDomains);
  const { run: choose, loading: choosing, error: chooseError } = useAction(api.chooseDomain);

  async function runSearch(keywordToSearch?: string) {
    const result = await search(run.id, keywordToSearch);
    if (result) {
      setDomains(result.domains);
      setSelected(null);
    }
  }

  useEffect(() => {
    void runSearch();
    // Search once when the step opens; later searches are started by the user.
  }, [run.id]);

  async function handleKeywordSubmit(event: FormEvent) {
    event.preventDefault();
    await runSearch(keyword.trim().toLowerCase());
  }

  async function handleChoose() {
    if (!selected) return;
    const updated = await choose(run.id, selected);
    if (updated) onChosen(updated);
  }

  return (
    <section className="card">
      <h1>Pick your domain</h1>

      {searching && <p>Searching for available domains…</p>}
      <ErrorMessage message={searchError} />

      {domains && domains.length > 0 && (
        <fieldset disabled={choosing}>
          <legend>Available domains</legend>
          {domains.map((domain) => (
            <label key={domain.name} className="option">
              <input
                type="radio"
                name="domain"
                value={domain.name}
                checked={selected === domain.name}
                onChange={() => setSelected(domain.name)}
              />
              <span>{domain.name}</span>
              <span className="price">{formatPrice(domain)}</span>
            </label>
          ))}
        </fieldset>
      )}

      {domains && domains.length === 0 && <p>No available domains found. Try different names below.</p>}

      {domains && (
        <>
          <ErrorMessage message={chooseError} />
          <button type="button" onClick={handleChoose} disabled={!selected || choosing}>
            {choosing ? "Writing your site… this can take about 20 seconds" : "Choose this domain"}
          </button>
        </>
      )}

      <form onSubmit={handleKeywordSubmit} className="keyword">
        <label htmlFor="keyword">Try different names</label>
        <input
          id="keyword"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          pattern="[A-Za-z0-9]([A-Za-z0-9\-]*[A-Za-z0-9])?"
          title="Use letters, numbers and hyphens, with no spaces."
          maxLength={63}
          placeholder="your-keyword"
          required
        />
        <button type="submit" disabled={searching || choosing}>
          Search
        </button>
      </form>
    </section>
  );
}
