"use client";

import { use } from "react";
import useSWR from "swr";
import ReactMarkdown from "react-markdown";
import { api } from "@/lib/api";
import type { ResultResponse } from "@/types";

export default function ResultPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const { data, error, isLoading } = useSWR<ResultResponse>(
    `result-${slug}`,
    () => api.getResult(slug)
  );

  if (isLoading) return <p className="text-sm text-gray-500">読み込み中…</p>;
  if (error) return (
    <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      ⚠️ {error.message}
    </div>
  );
  if (!data) return null;

  const meta = data.json_data as Record<string, string>;

  return (
    <div className="space-y-6">
      {/* メタ情報ヘッダー */}
      <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {meta.product_name ?? slug}
            </h1>
            <p className="mt-0.5 text-sm text-indigo-600">{meta.namespace}</p>
          </div>
          <span className="shrink-0 text-xs text-gray-400">{meta.last_updated}</span>
        </div>
        {meta.source_url && (
          <a
            href={meta.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-2 block text-xs text-blue-500 hover:underline truncate"
          >
            {meta.source_url}
          </a>
        )}
      </div>

      {/* Markdown ビューア */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold text-gray-700">抽出レポート</h2>
        <div className="prose prose-sm max-w-none text-gray-700">
          <ReactMarkdown>{data.markdown}</ReactMarkdown>
        </div>
      </div>

      {/* JSON アコーディオン */}
      <details className="rounded-xl border border-gray-200 bg-white shadow-sm">
        <summary className="cursor-pointer px-5 py-3 text-sm font-medium text-gray-600 hover:bg-gray-50">
          RAW JSON を表示
        </summary>
        <pre className="overflow-auto px-5 pb-5 text-xs text-gray-600">
          {JSON.stringify(data.json_data, null, 2)}
        </pre>
      </details>
    </div>
  );
}
