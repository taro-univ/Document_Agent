"use client";

import { useState } from "react";
import { ScoreBar } from "@/components/ScoreBar";
import type { DiscoveryProposal } from "@/types";

interface Props {
  proposal: DiscoveryProposal;
  onApprove: (url: string) => Promise<void>;
}

export function ProposalCard({ proposal, onApprove }: Props) {
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const score = proposal.signals.quality_score;

  async function handleApprove() {
    setLoading(true);
    try {
      await onApprove(proposal.url);
      setDone(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm space-y-2">
      {/* ヘッダー行 */}
      <div className="flex items-center justify-between gap-2">
        <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 truncate max-w-[60%]">
          {proposal.label}
        </span>
        <ScoreBar score={score} />
      </div>

      {/* タイトル・URL */}
      <p className="font-semibold text-sm text-gray-800 line-clamp-1">{proposal.title}</p>
      <a
        href={proposal.url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs text-blue-600 hover:underline truncate block"
      >
        {proposal.url}
      </a>

      {/* 採用理由 */}
      <p className="text-xs text-gray-500">{proposal.reasoning}</p>

      {/* Positive signals */}
      {proposal.signals.positive_signals.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {proposal.signals.positive_signals.map((s) => (
            <span key={s} className="text-[10px] bg-green-50 text-green-700 px-1.5 py-0.5 rounded">
              ✓ {s}
            </span>
          ))}
        </div>
      )}

      {/* Approve ボタン */}
      <button
        onClick={handleApprove}
        disabled={loading || done}
        className="mt-1 w-full rounded-lg bg-indigo-600 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {done ? "✓ 承認済み" : loading ? "処理中…" : "Approve & Extract"}
      </button>
    </div>
  );
}

