import { api } from "../../api/client";
import type { Run } from "../../api/types";
import { formatPrice, totalWithFees } from "../../utils/format";
import { useAction } from "../../hooks/useAction";
import { ErrorMessage } from "../ui/ErrorMessage";
import { Loading } from "../ui/Loading";

interface Props {
  run: Run;
  onConfirmed: (run: Run) => void;
  onBack: () => void;
}

export function ReviewStep({ run, onConfirmed, onBack }: Props) {
  const { run: generate, loading, error } = useAction(api.generateSite);
  const domain = run.domain;
  if (!domain) return null;
  const total = totalWithFees(domain.price, domain.fees, domain.currency);

  async function handleConfirm() {
    if (!domain) return;
    const updated = await generate(run.id, domain.name, domain.price);
    if (updated) onConfirmed(updated);
  }

  return (
    <section className="card">
      <h1>Check the price</h1>
      <p className="lead">Check the cost before we write your site. You'll see a preview next.</p>

      <div className="summary">
        <p className="summary-domain">{domain.name}</p>
        <p className="summary-price">
          <strong>{formatPrice(domain.price, domain.currency)}</strong>
          <span> first year</span>
        </p>
        {domain.fees.map((fee) => (
          <p key={fee.type} className="hint premium">
            Premium domain: plus a one-time fee of {formatPrice(fee.amount, fee.currency)}, charged when you buy
          </p>
        ))}
        {total !== null && (
          <p className="summary-total">
            Total first year: <strong>{formatPrice(total, domain.currency)}</strong>
            <span className="hint"> before ICANN fees and taxes</span>
          </p>
        )}
        {domain.renewal_price !== null && (
          <p className="hint">Renews at {formatPrice(domain.renewal_price, domain.currency)} per year</p>
        )}
      </div>

      <p className="notice">
        <strong>Nothing is purchased yet.</strong> Prices exclude taxes and fees and may change until you buy.
      </p>

      <ErrorMessage message={error} />
      {loading ? (
        <Loading
          message="Writing your site in English and Hindi…"
          detail="This takes about 20 seconds. Please keep this page open."
        />
      ) : (
        <div className="actions">
          <button type="button" onClick={handleConfirm}>
            Confirm and build my site
          </button>
          <button type="button" className="secondary" onClick={onBack}>
            Pick a different domain
          </button>
        </div>
      )}
    </section>
  );
}
