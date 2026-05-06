"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useJobs } from "@/hooks/useJobs";
import { ProposalCard } from "@/components/ProposalCard";
import { RejectedList } from "@/components/RejectedList";
import { JobStatusPoller } from "@/components/JobStatusPoller";
import type { DiscoverResponse } from "@/types";

export default function DiscoveryPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiscoverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { jobs, addJob } = useJobs();

  async function handleDiscover(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.discover({ query: query.trim() });
      setResult(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(url: string) {
    try {
      const job = await api.approve([url]);
      addJob(job);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Discovery</h1>
        <p className="mt-1 text-sm text-gray-500">
          リサーチクエリを入力すると、関連する技術ドキュメントを検索・評価して提案します。
        </p>
      </div>

      {/* 検索フォーム */}
      <form onSubmit={handleDiscover} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="例: GitHub Copilot pricing 2026"
          className="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2.5 text-sm shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-100"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "検索中…" : "検索"}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          ⚠️ {error}
        </div>
      )}

      {/* ジョブ進捗 */}
      {jobs.length > 0 && (
        <div className="space-y-2">
          {jobs.map((job) => (
            <JobStatusPoller key={job.job_id} jobId={job.job_id} />
          ))}
        </div>
      )}

      {/* 検索結果 */}
      {result && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              採用候補{" "}
              <span className="ml-1 rounded-full bg-indigo-100 px-2 py-0.5 text-sm text-indigo-700">
                {result.proposals.length}件
              </span>
            </h2>
            <p className="text-xs text-gray-400">
              catalog に {result.added_to_catalog} 件追加済み
            </p>
          </div>

          {result.proposals.length === 0 ? (
            <p className="text-sm text-gray-500">採用候補が見つかりませんでした。クエリを変えてみてください。</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {result.proposals.map((p) => (
                <ProposalCard key={p.url} proposal={p} onApprove={handleApprove} />
              ))}
            </div>
          )}

          <RejectedList rejected={result.rejected} />
        </div>
      )}
    </div>
  );
}
