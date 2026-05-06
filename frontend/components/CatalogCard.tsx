import { type ReactNode } from "react";
import Link from "next/link";
import { StatusBadge } from "./StatusBadge";
import type { CatalogEntry, CatalogStatus } from "@/types";

interface Props {
  entry: CatalogEntry;
  onApprove?: (url: string) => void;
  approving?: boolean;
}

type ActionCallbacks = Pick<Props, "onApprove" | "approving">;
type ActionRenderer = (entry: CatalogEntry, callbacks: ActionCallbacks) => ReactNode;

const STATUS_ACTIONS: Partial<Record<CatalogStatus, ActionRenderer>> = {
  proposed: (entry, { onApprove, approving }) =>
    onApprove ? (
      <button
        onClick={() => onApprove(entry.url)}
        disabled={approving}
        className="flex-1 rounded-lg bg-indigo-600 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {approving ? "処理中…" : "Approve"}
      </button>
    ) : null,

  extracted: (entry) => {
    const slug = entry.url.split("/").pop();
    return slug ? (
      <Link
        href={`/results/${slug}`}
        className="flex-1 rounded-lg border border-indigo-300 py-1.5 text-center text-xs font-medium text-indigo-600 hover:bg-indigo-50 transition-colors"
      >
        View Result
      </Link>
    ) : null;
  },
};

export function CatalogCard({ entry, onApprove, approving }: Props) {
  const action = STATUS_ACTIONS[entry.status]?.(entry, { onApprove, approving });

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
      <div className="flex items-center justify-between gap-2">
        <StatusBadge status={entry.status} />
        <span className="text-[10px] text-gray-400">{entry.last_updated}</span>
      </div>

      <p className="text-xs font-medium text-indigo-600 truncate">{entry.label}</p>

      <a
        href={entry.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-gray-700 hover:underline line-clamp-2 block"
      >
        {entry.url}
      </a>

      {entry.query && (
        <p className="text-[10px] text-gray-400">クエリ: {entry.query}</p>
      )}

      {action && <div className="flex gap-2 pt-1">{action}</div>}
    </div>
  );
}
