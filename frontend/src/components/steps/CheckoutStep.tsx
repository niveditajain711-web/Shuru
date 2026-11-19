import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { Run } from "../../api/types";
import { useAction } from "../../hooks/useAction";
import { formatPrice } from "../../utils/format";
import { ErrorMessage } from "../ui/ErrorMessage";
import { Loading } from "../ui/Loading";

interface Props {
  run: Run;
  onUpdated: (run: Run) => void;
  onBack: () => void;
  onStartOver: () => void;
}

const DEMO_NOTICE = "Demo mode: no domain will be registered and nothing will be charged.";

function isExpired(run: Run): boolean {
  return !run.quote || Date.parse(run.quote.expires_at) <= Date.now();
}

export function CheckoutStep({ run, onUpdated, onBack, onStartOver }: Props) {
  if (run.state === "purchased" && run.purchase) return <Done run={run} onStartOver={onStartOver} />;
  if (run.state === "purchasing") return <Pending run={run} onUpdated={onUpdated} />;
  return <Quoted run={run} onUpdated={onUpdated} onBack={onBack} />;
}

function Quoted({ run, onUpdated, onBack }: Omit<Props, "onStartOver">) {
  const { run: fetchQuote, loading: quoting, error: quoteError } = useAction(api.quotePurchase);
  const { run: buy, loading: buying, error: buyError } = useAction(api.purchase);
  const [agreed, setAgreed] = useState(false);
  const [feesAcknowledged, setFeesAcknowledged] = useState(false);
  const quote = run.quote;

  async function refreshQuote() {
    const updated = await fetchQuote(run.id);
    if (updated) {
      setAgreed(false);
      setFeesAcknowledged(false);
      onUpdated(updated);
    }
  }

  // The price is locked for a short time, so ask for a current one when the page opens.
  useEffect(() => {
    if (isExpired(run)) void refreshQuote();
  }, [run.id]);

  async function handleBuy() {
    if (!quote) return;
    const updated = await buy(run.id, {
      agreement_types: quote.agreements.map((a) => a.type),
      price: quote.price,
      acknowledged_fees: feesAcknowledged,
    });
    if (updated) onUpdated(updated);
  }

  const reviewedPrice = run.domain?.price;
  const hasFees = !!quote && quote.fees.length > 0;
  const ready = !!quote && agreed && (!hasFees || feesAcknowledged);
  const busy = quoting || buying;

  return (
    <section className="card">
      <h1>Buy your domain</h1>
      <p className="lead">Check the price and the agreements, then confirm your purchase.</p>

      {quote?.demo && (
        <p className="notice" role="note">
          <strong>{DEMO_NOTICE}</strong>
        </p>
      )}

      {quote ? (
        <>
          <div className="summary">
            <p className="summary-domain">{quote.domain}</p>
            <p className="summary-price">
              <strong>{formatPrice(quote.price, quote.currency)}</strong>
              <span> for {quote.period === 1 ? "the first year" : `${quote.period} years`}</span>
            </p>
            {quote.fees.map((fee) => (
              <p key={fee.type} className="hint">
                Plus a one-time premium domain fee of {formatPrice(fee.amount, fee.currency)}
              </p>
            ))}
            {quote.renewal_price !== null && (
              <p className="hint">Renews at {formatPrice(quote.renewal_price, quote.currency)} per year</p>
            )}
            <p className="hint">
              Price locked until {new Date(quote.expires_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}.
              Excludes ICANN fees and taxes, which are added at purchase.
            </p>
          </div>

          {reviewedPrice !== undefined && reviewedPrice !== quote.price && (
            <p className="notice" role="status">
              The price changed since you reviewed it: it was {formatPrice(reviewedPrice, quote.currency)}.
            </p>
          )}

          <div className="consent">
            {hasFees && (
              <label className="check">
                <input
                  type="checkbox"
                  checked={feesAcknowledged}
                  onChange={(e) => setFeesAcknowledged(e.target.checked)}
                  disabled={busy}
                />
                <span>I understand this premium domain has a one-time fee on top of the registration price.</span>
              </label>
            )}
            <label className="check">
              <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} disabled={busy} />
              <span>
                I have read and agree to{" "}
                {quote.agreements.map((agreement, i) => (
                  <span key={agreement.type}>
                    {i > 0 && ", "}
                    {agreement.url ? (
                      <a href={agreement.url} target="_blank" rel="noopener noreferrer">
                        {agreement.title}
                      </a>
                    ) : (
                      agreement.title
                    )}
                  </span>
                ))}
                .
              </span>
            </label>
          </div>
        </>
      ) : (
        quoting && <Loading message="Getting your price…" detail="This locks the price for a few minutes." />
      )}

      <ErrorMessage message={quoteError ?? buyError} />
      {buying ? (
        <Loading
          message={quote?.demo ? "Completing your demo purchase…" : "Registering your domain…"}
          detail="Please keep this page open."
        />
      ) : (
        <div className="actions">
          <button type="button" onClick={handleBuy} disabled={!ready || busy}>
            {quote?.demo ? "Complete demo purchase" : "Buy domain"}
          </button>
          {(quote || quoteError || buyError) && (
            <button type="button" className="secondary" onClick={refreshQuote} disabled={busy}>
              Get the current price
            </button>
          )}
          <button type="button" className="secondary" onClick={onBack} disabled={busy}>
            Back to preview
          </button>
        </div>
      )}
    </section>
  );
}

function Pending({ run, onUpdated }: Pick<Props, "run" | "onUpdated">) {
  const { run: refresh, loading, error } = useAction(api.refreshPurchase);

  async function handleRefresh() {
    const updated = await refresh(run.id);
    if (updated) onUpdated(updated);
  }

  return (
    <section className="card">
      <h1>Registering your domain</h1>
      <p className="lead">
        <strong>{run.purchase?.domain}</strong> is still being registered. This can take a few minutes. You don't need to
        pay again.
      </p>
      <ErrorMessage message={error} />
      {loading ? (
        <Loading message="Checking…" />
      ) : (
        <div className="actions">
          <button type="button" onClick={handleRefresh}>
            Check status
          </button>
        </div>
      )}
    </section>
  );
}

function Done({ run, onStartOver }: Pick<Props, "run" | "onStartOver">) {
  const purchase = run.purchase;
  if (!purchase) return null;
  return (
    <section className="card">
      <h1>{purchase.demo ? "Demo purchase complete" : "Your domain is registered"}</h1>
      {purchase.demo ? (
        <p className="notice" role="note">
          <strong>{DEMO_NOTICE}</strong> This is how the confirmation will look.
        </p>
      ) : (
        <p className="lead">Thank you. The domain is now yours.</p>
      )}
      <div className="summary">
        <p className="summary-domain">{purchase.domain}</p>
        <p className="summary-price">
          <strong>{formatPrice(purchase.price, purchase.currency)}</strong>
          <span> {purchase.demo ? "(not charged)" : "first year, before ICANN fees and taxes"}</span>
        </p>
        {purchase.expires_at && (
          <p className="hint">Registered until {new Date(purchase.expires_at).toLocaleDateString()}</p>
        )}
      </div>
      <div className="actions">
        <button type="button" onClick={onStartOver}>
          Start a new site
        </button>
      </div>
    </section>
  );
}
