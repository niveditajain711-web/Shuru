// Mirrors the backend models in backend/app/models.py.

export type Lang = "en" | "hi";

export type RunState =
  | "briefed"
  | "domains_listed"
  | "domain_chosen"
  | "site_generated"
  | "purchasing"
  | "purchased";

export interface Brief {
  audience: string;
  tone: string;
  tagline: string;
  name_ideas: string[];
}

/** A one-time fee on a premium (aftermarket) domain, charged on top of the registration price. */
export interface PremiumFee {
  type: string;
  currency: string;
  value: number;
  amount: number;
}

export interface DomainOffer {
  name: string;
  price: number; // first-year price, excluding ICANN fees and taxes
  renewal_price: number | null;
  currency: string;
  fees: PremiumFee[]; // premium domains only; empty for ordinary ones
}

export interface Agreement {
  type: string;
  title: string;
  url: string | null;
}

/** A price locked by GoDaddy for a short time. Excludes ICANN fees and taxes. */
export interface Quote {
  domain: string;
  period: number;
  price: number;
  renewal_price: number | null;
  currency: string;
  fees: PremiumFee[];
  agreements: Agreement[];
  expires_at: string;
  demo: boolean;
}

export interface Purchase {
  domain: string;
  status: "pending" | "completed";
  demo: boolean; // true: nothing was registered or charged
  price: number;
  currency: string;
  registration_id: string | null;
  agreed_at: string;
  expires_at: string | null;
}

export interface PurchaseConsent {
  agreement_types: string[];
  price: number;
  acknowledged_fees: boolean;
}

export interface Run {
  id: string;
  state: RunState;
  lang: Lang;
  idea: string;
  brief: Brief;
  domains: DomainOffer[];
  domain: DomainOffer | null;
  quote: Quote | null;
  purchase: Purchase | null;
  regenerations: number;
}

export interface ContactMessage {
  name: string;
  email: string;
  message: string;
  website: string; // honeypot, always empty for real visitors
}
