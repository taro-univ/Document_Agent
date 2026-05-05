import Link from "next/link";
import { StatusBadge } from "./StatusBadge";
import type { CatalogEntry } from "@/types";

interface Props {
  entry: CatalogEntry;
  onApprove?: (url: string) => void;
  approving?: boolean;
}

export function CatalogCard({ entry, onApprove, approving }: Props) {
  const slug = entry.url.split("/").pop() ?? "";

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

      <div className="flex gap-2 pt-1">
        {entry.status === "proposed" && onApprove && (
          <button
            onClick={() => onApprove(entry.url)}
            disabled={approving}
            className="flex-1 rounded-lg bg-indigo-600 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {approving ? "処理中…" : "Approve"}
          </button>
        )}
        {entry.status === "extracted" && slug && (
          <Link
            href={`/results/${slug}`}
            className="flex-1 rounded-lg border border-indigo-300 py-1.5 text-center text-xs font-medium text-indigo-600 hover:bg-indigo-50 transition-colors"
          >
            View Result
          </Link>
        )}
      </div>
    </div>
  );
}
