// Mirrors the backend models in backend/app/models.py.

export type Lang = "en" | "hi";

export type RunState = "briefed" | "domains_listed" | "domain_chosen" | "site_generated";

export interface Brief {
  audience: string;
  tone: string;
  tagline: string;
  name_ideas: string[];
}

export interface DomainOffer {
  name: string;
  price: number; // first-year price, excluding taxes and fees
  renewal_price: number | null;
  currency: string;
}

export interface Run {
  id: string;
  state: RunState;
  lang: Lang;
  idea: string;
  brief: Brief;
  domains: DomainOffer[];
  domain: DomainOffer | null;
  regenerations: number;
}
