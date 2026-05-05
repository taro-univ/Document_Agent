import type {
  CatalogResponse,
  DiscoverResponse,
  JobResponse,
  ResultResponse,
  StatusResponse,
} from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getStatus: () => request<StatusResponse>("/api/status"),

  getCatalog: () => request<CatalogResponse>("/api/catalog"),

  discover: (body: {
    query: string;
    max_results?: number;
    search_provider?: "brave" | "google";
    quality_threshold?: number;
  }) =>
    request<DiscoverResponse>("/api/discover", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  approve: (urls: string[]) =>
    request<JobResponse>("/api/approve", {
      method: "POST",
      body: JSON.stringify({ urls }),
    }),

  approveAll: () =>
    request<JobResponse>("/api/approve-all", { method: "POST" }),

  getJob: (jobId: string) => request<JobResponse>(`/api/jobs/${jobId}`),

  getResult: (slug: string) => request<ResultResponse>(`/api/results/${slug}`),
};
