from __future__ import annotations

from src.extraction_models import BenchmarkReport, DocumentExtraction


def to_markdown(r: DocumentExtraction) -> str:
    lines: list[str] = [
        f"# {r.product_name} ({r.namespace})",
        f"**Source**: {r.source_url}  |  **Last Updated**: {r.last_updated}",
        "",
        "## 価格・プラン",
        f"- **課金方式**: {r.billing.billing_model}",
        f"- **対象プラン**: {', '.join(r.billing.plans_available)}",
        f"- **使用制限**: {r.billing.usage_limits}",
        "",
        "## 技術仕様",
        f"- **AIモデル**: {', '.join(r.tech_spec.ai_models)}",
        f"- **対応エコシステム**: {', '.join(r.tech_spec.supported_ecosystems)}",
        f"- **インターフェース**: {', '.join(r.tech_spec.interface_tools)}",
        "",
        "## 活用シーン",
        f"- **ユースケース**: {', '.join(r.use_case_info.use_cases)}",
        f"- **カスタムエージェント**: {r.use_case_info.custom_agents}",
        "",
        "## コマンド例",
    ]
    for cmd in r.commands_scripts:
        lines.append(f"```\n{cmd}\n```")
    lines += ["", "## 注意事項"]
    for note in r.constraints_notes:
        lines.append(f"- {note}")
    if r.timeline:
        lines += [
            "",
            "## 移行スケジュール（2026年6月）",
            f"- **[Current]**: {r.timeline.current}",
            f"- **[Post-June 2026]**: {r.timeline.post_june_2026}",
        ]
    if r.embedded_relevance:
        lines += ["", "## 組み込み開発への適用", r.embedded_relevance]
    return "\n".join(lines) + "\n"


def benchmark_to_markdown(report: BenchmarkReport) -> str:
    lines = ["# Benchmark Report", f"**URL**: {report.url}", ""]
    lines += ["| Provider | Model | Elapsed (s) |", "|---|---|---|"]
    for e in report.entries:
        lines.append(f"| {e.provider} | {e.model_name} | {e.elapsed_sec} |")
    lines.append("")
    for e in report.entries:
        lines += [f"## {e.provider} / {e.model_name}", to_markdown(e.extraction), ""]
    return "\n".join(lines)
