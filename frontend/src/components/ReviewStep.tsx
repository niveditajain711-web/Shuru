import { api } from "../api/client";
import type { Run } from "../api/types";
import { formatPrice } from "../format";
import { useAction } from "../hooks/useAction";
import { ErrorMessage } from "./ErrorMessage";

interface Props {
  run: Run;
  onConfirmed: (run: Run) => void;
  onBack: () => void;
}

export function ReviewStep({ run, onConfirmed, onBack }: Props) {
  const { run: generate, loading, error } = useAction(api.generateSite);
  const domain = run.domain;
  if (!domain) return null;

  async function handleConfirm() {
    if (!domain) return;
    const updated = await generate(run.id, domain.name, domain.price);
    if (updated) onConfirmed(updated);
  }

  return (
    <section className="card">
      <h1>Review your domain</h1>
      <dl>
        <dt>Domain</dt>
        <dd>
          <strong>{domain.name}</strong>
        </dd>
        <dt>First year</dt>
        <dd>{formatPrice(domain.price, domain.currency)}</dd>
        {domain.renewal_price !== null && (
          <>
            <dt>Renews at</dt>
            <dd>{formatPrice(domain.renewal_price, domain.currency)} per year</dd>
          </>
        )}
      </dl>
      <p>
        Prices exclude taxes and fees and may change until you buy. Nothing is purchased yet: we only build a preview
        of your site.
      </p>

      <ErrorMessage message={error} />
      <button type="button" onClick={handleConfirm} disabled={loading}>
        {loading ? "Writing your site… this can take about 20 seconds" : "Confirm and build my site"}
      </button>
      <button type="button" onClick={onBack} disabled={loading}>
        Pick a different domain
      </button>
    </section>
  );
}
