export type Role = "admin" | "analyst" | "readonly";
export type AlertChannel = "email" | "slack" | "webhook";

export interface User {
  id: number;
  email: string;
  role: Role;
  is_active: boolean;
}

export interface Source {
  id: number;
  name: string;
  onion_url: string;
  crawl_frequency_hours: number;
  last_crawled_at: string | null;
  is_active: boolean;
  created_at: string;
  created_by_id: number | null;
}

export interface Finding {
  id: number;
  source_id: number;
  url: string;
  title: string | null;
  content_snippet: string;
  matched_keywords: string[];
  first_seen: string;
  last_seen: string;
}

export interface FindingsPage {
  items: Finding[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchHit {
  id: string;
  score: number;
  url: string | null;
  title: string | null;
  source_id: number | null;
  matched_keywords: string[];
  highlights: string[];
}

export interface Watchlist {
  id: number;
  name: string;
  owner_id: number;
  keywords: string[];
  domains: string[];
  emails: string[];
  is_active: boolean;
  created_at: string;
}

export interface Alert {
  id: number;
  watchlist_id: number;
  finding_id: number;
  triggered_at: string;
  channel: AlertChannel;
  delivered: boolean;
  acknowledged: boolean;
  acknowledged_at: string | null;
}

export interface AlertConfig {
  id: number;
  watchlist_id: number;
  channel: AlertChannel;
  destination: string;
  is_active: boolean;
  created_at: string;
}
