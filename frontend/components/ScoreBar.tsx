interface Props {
  score: number;
}

export function ScoreBar({ score }: Props) {
  const color = score >= 8 ? "bg-green-500" : score >= 6 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-1.5 shrink-0">
      <div className="w-20 h-1.5 rounded-full bg-gray-200">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${score * 10}%` }} />
      </div>
      <span className="text-xs text-gray-500">{score}/10</span>
    </div>
  );
}
