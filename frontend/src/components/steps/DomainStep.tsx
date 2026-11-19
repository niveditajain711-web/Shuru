import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../api/client";
import type { Run } from "../../api/types";
import { formatPrice } from "../../utils/format";
import { useAction } from "../../hooks/useAction";
import { BusinessSummary } from "../ui/BusinessSummary";
import { ErrorMessage } from "../ui/ErrorMessage";
import { Loading } from "../ui/Loading";

interface Props {
  run: Run;
  /** Called with the run after a search, so the list survives going to another step and back. */
  onUpdated: (run: Run) => void;
  onChosen: (run: Run) => void;
}

export function DomainStep({ run, onUpdated, onChosen }: Props) {
  const [selected, setSelected] = useState<string | null>(run.domain?.name ?? null);
  const [keyword, setKeyword] = useState("");
  const [lastKeyword, setLastKeyword] = useState<string | undefined>();
  const { run: search, loading: searching, error: searchError } = useAction(api.listDomains);
  const { run: choose, loading: choosing, error: chooseError } = useAction(api.chooseDomain);

  // A run that has not been searched yet is searched when the step opens. After that the saved list
  // is shown as it is, so going back to this step does not repeat the external calls.
  const needsSearch = run.state === "briefed";
  const showSkeleton = searching || (needsSearch && !searchError);
  const domains = run.domains;

  // Tapping a name idea searches for it; tapping it again goes back to the default suggestions.
  const activeName = run.brief.name_ideas.find((name) => name === lastKeyword);

  async function handlePickName(name: string) {
    const next = activeName === name ? undefined : name;
    setKeyword(next ?? "");
    await runSearch(next);
  }

  async function runSearch(keywordToSearch?: string) {
    setLastKeyword(keywordToSearch);
    const result = await search(run.id, keywordToSearch);
    if (result) {
      onUpdated(result);
      setSelected(null);
    }
  }

  useEffect(() => {
    if (needsSearch) void runSearch();
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
      <h1>Choose your domain</h1>
      <p className="lead">
        These domains are available to register. Prices are for the first year and exclude taxes and fees.
      </p>

      <BusinessSummary
        run={run}
        activeName={activeName}
        onPickName={(name) => void handlePickName(name)}
        disabled={searching || choosing}
      />

      <form onSubmit={handleKeywordSubmit} className="keyword">
        <label htmlFor="keyword">Looking for something else?</label>
        <div className="row">
          <input
            id="keyword"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            pattern="[A-Za-z0-9]([A-Za-z0-9\-]*[A-Za-z0-9])?"
            title="Use letters, numbers and hyphens, with no spaces."
            maxLength={63}
            placeholder="your-keyword"
            aria-describedby="keyword-hint"
            required
          />
          <button type="submit" className="secondary" disabled={searching || choosing}>
            Search
          </button>
        </div>
        <p id="keyword-hint" className="hint">
          One word works best, for example "achaar". Use letters, numbers and hyphens.
        </p>
      </form>

      {showSkeleton && (
        <>
          <Loading message="Searching for available domains…" />
          <div aria-hidden="true" className="skeletons">
            {[0, 1, 2, 3].map((index) => (
              <div key={index} className="skeleton" />
            ))}
          </div>
        </>
      )}

      {searchError && (
        <div className="error-box">
          <ErrorMessage message={searchError} />
          <button type="button" className="secondary" disabled={searching} onClick={() => void runSearch(lastKeyword)}>
            Try again
          </button>
        </div>
      )}

      {!showSkeleton && !needsSearch && domains.length > 0 && (
        <fieldset disabled={choosing}>
          <legend>
            {domains.length} available {domains.length === 1 ? "domain" : "domains"}
            {lastKeyword && <> for “{lastKeyword}”</>}
          </legend>
          {domains.map((domain) => (
            <label key={domain.name} className="domain-card">
              <input
                type="radio"
                name="domain"
                value={domain.name}
                checked={selected === domain.name}
                onChange={() => setSelected(domain.name)}
              />
              <span className="domain-name">{domain.name}</span>
              <span className="domain-price">
                <strong>{formatPrice(domain.price, domain.currency)}</strong>
                <span className="hint">first year</span>
                {domain.renewal_price !== null && (
                  <span className="hint">renews at {formatPrice(domain.renewal_price, domain.currency)}/yr</span>
                )}
                {domain.fees.map((fee) => (
                  <span key={fee.type} className="hint premium">
                    Premium domain: plus a one-time fee of {formatPrice(fee.amount, fee.currency)}
                  </span>
                ))}
              </span>
            </label>
          ))}
        </fieldset>
      )}

      {!showSkeleton && !needsSearch && domains.length === 0 && !searchError && (
        <p className="empty">No available domains found. Try a different word above.</p>
      )}

      {!showSkeleton && !needsSearch && domains.length > 0 && (
        <>
          <ErrorMessage message={chooseError} />
          {choosing ? (
            <Loading message="Checking availability…" />
          ) : (
            <div className="actions">
              <button type="button" onClick={handleChoose} disabled={!selected}>
                Choose this domain
              </button>
            </div>
          )}
        </>
      )}
    </section>
  );
}
