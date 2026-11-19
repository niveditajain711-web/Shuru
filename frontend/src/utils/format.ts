import type { PremiumFee } from "../api/types";

export function formatPrice(amount: number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
}

/** The registration price plus premium fees, or null when there are no fees or one is in another currency. */
export function totalWithFees(price: number, fees: PremiumFee[], currency: string): number | null {
  if (fees.length === 0 || fees.some((fee) => fee.currency !== currency)) return null;
  return price + fees.reduce((sum, fee) => sum + fee.amount, 0);
}
