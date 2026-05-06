// バックエンドの Pydantic スキーマと 1:1 対応

export type CatalogStatus = "proposed" | "approved" | "fetched" | "extracted";

export interface DiscoverySignals {
  is_technical_resource: boolean;
  quality_score: number;
  positive_signals: string[];
  negative_signals: string[];
}

export interface DiscoveryProposal {
  url: string;
  title: string;
  snippet: string;
  label: string;
  signals: DiscoverySignals;
  reasoning: string;
}

export interface CatalogEntry {
  url: string;
  label: string;
  status: CatalogStatus;
  local_path: string | null;
  query: string | null;
  last_updated: string;
}

export type JobStatus = "pending" | "running" | "done" | "error";

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  total: number;
  completed: number;
  failed: string[];
}

export interface CatalogResponse {
  entries: CatalogEntry[];
  total: number;
}

export interface StatusResponse {
  proposed: number;
  approved: number;
  fetched: number;
  extracted: number;
  total: number;
}

export interface DiscoverResponse {
  proposals: DiscoveryProposal[];
  rejected: DiscoveryProposal[];
  added_to_catalog: number;
}

export interface ResultResponse {
  slug: string;
  json_data: Record<string, unknown>;
  markdown: string;
}
