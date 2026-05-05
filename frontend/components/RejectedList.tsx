"use client";

import { useState } from "react";
import type { DiscoveryProposal } from "@/types";

export function RejectedList({ rejected }: { rejected: DiscoveryProposal[] }) {
  const [open, setOpen] = useState(false);

  if (rejected.length === 0) return null;

  return (
    <div className="rounded-xl border border-red-100 bg-red-50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-red-700"
      >
        <span>❌ 却下 {rejected.length} 件</span>
        <span>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <ul className="divide-y divide-red-100 px-4 pb-3 space-y-2">
          {rejected.map((p) => (
            <li key={p.url} className="pt-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded">
                  score:{p.signals.quality_score}
                </span>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-gray-600 hover:underline truncate"
                >
                  {p.url}
                </a>
              </div>
              <p className="mt-0.5 text-xs text-gray-400">{p.reasoning}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
