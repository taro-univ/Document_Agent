"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { JobResponse } from "@/types";

interface JobLabels {
  running?: string;
  done?: string;
  error?: string;
}

interface Props {
  jobId: string;
  onDone?: () => void;
  pollingInterval?: number;
  labels?: JobLabels;
}

const DEFAULT_LABELS: Required<JobLabels> = {
  running: "⏳ 抽出中…",
  done: "✅ 抽出完了",
  error: "⚠️ 一部エラー",
};

export function JobStatusPoller({
  jobId,
  onDone,
  pollingInterval = 2000,
  labels,
}: Props) {
  const resolvedLabels = { ...DEFAULT_LABELS, ...labels };

  const { data } = useSWR<JobResponse>(
    `job-${jobId}`,
    () => api.getJob(jobId),
    {
      refreshInterval: (data) =>
        data?.status === "done" || data?.status === "error" ? 0 : pollingInterval,
      onSuccess: (data) => {
        if ((data.status === "done" || data.status === "error") && onDone) {
          onDone();
        }
      },
    }
  );

  if (!data) return null;

  const pct = data.total > 0 ? Math.round((data.completed / data.total) * 100) : 0;
  const isDone = data.status === "done";
  const isError = data.status === "error";

  return (
    <div className="rounded-xl border border-indigo-100 bg-indigo-50 p-4 space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-indigo-700">
          {isDone ? resolvedLabels.done : isError ? resolvedLabels.error : resolvedLabels.running}
        </span>
        <span className="text-indigo-500 text-xs">
          {data.completed} / {data.total} 件
        </span>
      </div>

      {/* プログレスバー */}
      <div className="h-2 w-full rounded-full bg-indigo-200">
        <div
          className={`h-full rounded-full transition-all duration-500 ${
            isError ? "bg-red-400" : "bg-indigo-500"
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {data.failed.length > 0 && (
        <ul className="text-xs text-red-600 space-y-0.5">
          {data.failed.map((url) => (
            <li key={url}>✗ {url}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
