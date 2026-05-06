"use client";

import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useJobs } from "@/hooks/useJobs";
import { CatalogCard } from "@/components/CatalogCard";
import { JobStatusPoller } from "@/components/JobStatusPoller";
import type { CatalogResponse, CatalogStatus } from "@/types";

const TABS: { label: string; value: CatalogStatus | "all" }[] = [
  { label: "All", value: "all" },
  { label: "Proposed", value: "proposed" },
  { label: "Approved", value: "approved" },
  { label: "Extracted", value: "extracted" },
];

export default function CatalogPage() {
  const [tab, setTab] = useState<CatalogStatus | "all">("all");
  const [approvingUrl, setApprovingUrl] = useState<string | null>(null);
  const { jobs, addJob } = useJobs();
  const [error, setError] = useState<string | null>(null);

  const { data, mutate } = useSWR<CatalogResponse>("catalog", api.getCatalog, {
    refreshInterval: 5000,
  });

  const entries = data?.entries ?? [];
  const filtered = tab === "all" ? entries : entries.filter((e) => e.status === tab);

  async function handleApprove(url: string) {
    setApprovingUrl(url);
    setError(null);
    try {
      const job = await api.approve([url]);
      addJob(job);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setApprovingUrl(null);
    }
  }

  async function handleApproveAll() {
    setError(null);
    try {
      const job = await api.approveAll();
      addJob(job);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  const proposedCount = entries.filter((e) => e.status === "proposed").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Catalog</h1>
          <p className="mt-1 text-sm text-gray-500">
            登録済みリソースの一覧とステータス管理
          </p>
        </div>
        {proposedCount > 0 && (
          <button
            onClick={handleApproveAll}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
          >
            Approve All ({proposedCount})
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          ⚠️ {error}
        </div>
      )}

      {/* ジョブ進捗 */}
      {jobs.length > 0 && (
        <div className="space-y-2">
          {jobs.map((job) => (
            <JobStatusPoller key={job.job_id} jobId={job.job_id} onDone={mutate} />
          ))}
        </div>
      )}

      {/* タブ */}
      <div className="flex gap-2 border-b border-gray-200">
        {TABS.map((t) => {
          const count = t.value === "all"
            ? entries.length
            : entries.filter((e) => e.status === t.value).length;
          return (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={`pb-2 px-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.value
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
              <span className="ml-1.5 rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                {count}
              </span>
            </button>
          );
        })}
      </div>

      {/* エントリ一覧 */}
      {filtered.length === 0 ? (
        <p className="text-sm text-gray-500 py-8 text-center">
          {tab === "all" ? "エントリがありません。Discoveryでリソースを探してください。" : `${tab} なエントリがありません。`}
        </p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((entry) => (
            <CatalogCard
              key={entry.url}
              entry={entry}
              onApprove={handleApprove}
              approving={approvingUrl === entry.url}
            />
          ))}
        </div>
      )}
    </div>
  );
}
