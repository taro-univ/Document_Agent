from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

import src.catalog as catalog
from src.discovery import discover
from src.extractor import Provider, benchmark, extract
from src.extraction_models import BenchmarkReport, DocumentExtraction
from src.formatter import benchmark_to_markdown, to_markdown
from src.models import CatalogEntry, DiscoveryResult
from src.scraper import fetch_and_clean, fetch_supplements, slug_from_url

load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_URLS: list[str] = [
    "https://docs.github.com/en/copilot/about-github-copilot/what-is-github-copilot",
    "https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-copilot/about-billing-for-github-copilot",
    "https://docs.github.com/en/github-models/about-github-models",
]

_EMPTY_VALUES = {"記載なし", "", "不明"}

# ── 抽出ヘルパー ─────────────────────────────────────────────────────────

def _is_empty(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0 or all(str(v).strip() in _EMPTY_VALUES for v in value)
    if isinstance(value, str):
        return value.strip() in _EMPTY_VALUES
    return False


def _detect_empty_fields(r: DocumentExtraction) -> list[str]:
    empty: list[str] = []
    if _is_empty(r.tech_spec.ai_models):
        empty.append("ai_models")
    if _is_empty(r.tech_spec.supported_ecosystems):
        empty.append("supported_ecosystems")
    if _is_empty(r.tech_spec.interface_tools):
        empty.append("interface_tools")
    if _is_empty(r.commands_scripts):
        empty.append("commands_scripts")
    if _is_empty(r.use_case_info.custom_agents):
        empty.append("custom_agents")
    return empty


def _merge(pass1: DocumentExtraction, pass2: DocumentExtraction) -> DocumentExtraction:
    d1 = pass1.model_dump()
    d2 = pass2.model_dump()

    if _is_empty(pass1.tech_spec.ai_models) and not _is_empty(pass2.tech_spec.ai_models):
        d1["tech_spec"]["ai_models"] = d2["tech_spec"]["ai_models"]
    if _is_empty(pass1.tech_spec.supported_ecosystems) and not _is_empty(pass2.tech_spec.supported_ecosystems):
        d1["tech_spec"]["supported_ecosystems"] = d2["tech_spec"]["supported_ecosystems"]
    if _is_empty(pass1.tech_spec.interface_tools) and not _is_empty(pass2.tech_spec.interface_tools):
        d1["tech_spec"]["interface_tools"] = d2["tech_spec"]["interface_tools"]
    if _is_empty(pass1.commands_scripts) and not _is_empty(pass2.commands_scripts):
        d1["commands_scripts"] = d2["commands_scripts"]
    if _is_empty(pass1.use_case_info.custom_agents) and not _is_empty(pass2.use_case_info.custom_agents):
        d1["use_case_info"]["custom_agents"] = d2["use_case_info"]["custom_agents"]
    if pass1.timeline is None and pass2.timeline is not None:
        d1["timeline"] = d2["timeline"]
    if _is_empty(pass1.embedded_relevance) and not _is_empty(pass2.embedded_relevance):
        d1["embedded_relevance"] = d2["embedded_relevance"]

    d1["constraints_notes"] = pass1.constraints_notes + [
        n for n in pass2.constraints_notes if n not in pass1.constraints_notes
    ]
    return DocumentExtraction(**d1)


def _save(slug: str, result: DocumentExtraction) -> None:
    (OUTPUT_DIR / f"{slug}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (OUTPUT_DIR / f"{slug}.md").write_text(to_markdown(result), encoding="utf-8")


# ── コアコマンド ─────────────────────────────────────────────────────────

def process_url(url: str, force_refresh: bool = False, provider: Provider = "github_models") -> str:
    """2パス抽出を実行して出力ファイルを保存する。保存したJSONパスを返す。"""
    slug = slug_from_url(url)

    print(f"[pass1/fetch]   {url}")
    main_content = fetch_and_clean(url, force_refresh=force_refresh)

    print(f"[pass1/extract] {url}")
    pass1_result = extract(url, main_content, provider=provider)

    empty_fields = _detect_empty_fields(pass1_result)
    if not empty_fields:
        print("[pass1/complete] 空欄なし → Pass 2 をスキップ")
        _save(slug, pass1_result)
        print(f"[saved] {slug}.json / {slug}.md\n")
        return str(OUTPUT_DIR / f"{slug}.json")

    print(f"[pass1/empty] 空欄フィールド: {', '.join(empty_fields)}")

    supplement = fetch_supplements(url, force_refresh=force_refresh)
    if supplement is None:
        print("[pass2/skip] 補完URLが未定義 → Pass 1 結果をそのまま保存")
        _save(slug, pass1_result)
        print(f"[saved] {slug}.json / {slug}.md\n")
        return str(OUTPUT_DIR / f"{slug}.json")

    combined_content = f"{main_content}\n\n---\n\n{supplement}"

    print(f"[pass2/extract] {url}")
    pass2_result = extract(url, combined_content, provider=provider, is_pass2=True)

    final = _merge(pass1_result, pass2_result)
    filled = [f for f in empty_fields if not _is_empty(
        getattr(final.tech_spec, f, None) or getattr(final, f, None)
    )]
    print(f"[pass2/filled]  補完済みフィールド: {', '.join(filled) if filled else 'なし'}")

    _save(slug, final)
    print(f"[saved] {slug}.json / {slug}.md\n")
    return str(OUTPUT_DIR / f"{slug}.json")


def benchmark_url(url: str, force_refresh: bool = False) -> None:
    print(f"[fetch]   {url}")
    content = fetch_and_clean(url, force_refresh=force_refresh)
    print(f"[benchmark] {url}")
    report = benchmark(url, content)
    slug = slug_from_url(url)
    (OUTPUT_DIR / f"{slug}_benchmark.json").write_text(
        report.model_dump_json(indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / f"{slug}_benchmark.md").write_text(
        benchmark_to_markdown(report), encoding="utf-8"
    )
    print(f"[saved] {slug}_benchmark.json / {slug}_benchmark.md\n")


def cmd_discover(
    query: str,
    search_provider: str = "brave",
    max_results: int = 10,
    quality_threshold: int = 6,
) -> None:
    """検索 → LLM評価 → catalog登録 → 結果表示。"""
    existing_labels = catalog.get_labels()
    result = discover(
        query,
        max_results=max_results,
        search_provider=search_provider,  # type: ignore[arg-type]
        existing_labels=existing_labels or None,
        quality_threshold=quality_threshold,
    )
    catalog.add_proposals(result)
    _print_discovery_result(result)


def cmd_approve_all(force_refresh: bool = False) -> None:
    """proposed を全承認し、各URLの2パス抽出を実行する。"""
    proposed = catalog.list_by_status("proposed")
    if not proposed:
        print("[approve-all] proposed なエントリがありません。")
        print("  まず --discover でリソースを探してください。")
        _print_catalog_summary()
        return

    print(f"[approve-all] {len(proposed)} 件を承認して抽出を開始します")
    _print_catalog_summary()
    print()

    catalog.approve_all()

    for entry in proposed:
        print(f"─── {entry.url}")
        try:
            json_path = process_url(entry.url, force_refresh=force_refresh)
            catalog.set_status(
                entry.url,
                "extracted",
                local_path=str(Path(json_path).relative_to(Path(__file__).parent.parent)),
            )
        except Exception as e:
            print(f"[error] {entry.url}: {e}", file=sys.stderr)

    print()
    _print_catalog_summary()


# ── 表示ヘルパー ─────────────────────────────────────────────────────────

def _print_discovery_result(result: DiscoveryResult) -> None:
    sep = "═" * 60
    print()
    print(sep)
    print(f' Discovery: "{result.query}"')
    print(sep)

    if result.proposals:
        print(f"\n ✅ 採用候補  {len(result.proposals)} 件\n")
        for i, p in enumerate(result.proposals, 1):
            score_bar = "█" * p.signals.quality_score + "░" * (10 - p.signals.quality_score)
            print(f"  #{i}  [{score_bar}] score:{p.signals.quality_score}  {p.label}")
            print(f"       URL: {p.url}")
            print(f"       → {p.reasoning}")
            if p.signals.positive_signals:
                print(f"       ✓ {' / '.join(p.signals.positive_signals)}")
            print()
    else:
        print("\n ✅ 採用候補: 0件\n")

    if result.rejected:
        print(f" ❌ 却下  {len(result.rejected)} 件\n")
        for p in result.rejected:
            print(f"  - [score:{p.signals.quality_score}] {p.url}")
            print(f"    {p.reasoning}")
        print()

    print(sep)
    print(f" catalog に {len(result.proposals)} 件を proposed として登録しました。")
    print(" 次のステップ: python -m src.main --approve-all")
    print(sep)
    print()


def _print_catalog_summary() -> None:
    s = catalog.summary()
    total = sum(s.values())
    print(
        f"[catalog] total:{total}  "
        f"proposed:{s['proposed']}  "
        f"approved:{s['approved']}  "
        f"fetched:{s['fetched']}  "
        f"extracted:{s['extracted']}"
    )




# ── エントリーポイント ───────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="GitHub Documentation Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # URLを直接抽出（デフォルトリストを使用）
  python -m src.main

  # 特定URLを抽出
  python -m src.main https://docs.github.com/en/copilot/...

  # Webから検索して候補を提案
  python -m src.main --discover "GitHub Copilot pricing 2026"

  # 提案された全URLを承認して抽出
  python -m src.main --approve-all

  # カタログの状態を表示
  python -m src.main --catalog

  # ベンチマーク（複数モデル比較）
  python -m src.main --benchmark
        """,
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--discover",
        metavar="QUERY",
        help="リサーチクエリで検索・LLM評価・catalog登録",
    )
    mode.add_argument(
        "--approve-all",
        action="store_true",
        help="proposed を全承認して2パス抽出を実行",
    )
    mode.add_argument(
        "--benchmark",
        action="store_true",
        help="複数LLMプロバイダーで抽出精度を比較",
    )
    mode.add_argument(
        "--catalog",
        action="store_true",
        help="catalog.json のサマリーを表示",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="キャッシュを無視して再取得",
    )
    parser.add_argument(
        "--search-provider",
        default="brave",
        choices=["brave", "google"],
        help="検索APIプロバイダー (default: brave)",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        metavar="N",
        help="検索API取得件数 (default: 10)",
    )
    parser.add_argument(
        "--quality-threshold",
        type=int,
        default=6,
        metavar="N",
        help="採用とみなすスコア下限 (default: 6, range: 1-10)",
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="抽出対象URL（省略時はデフォルトリストを使用）",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.discover:
        cmd_discover(
            args.discover,
            search_provider=args.search_provider,
            max_results=args.max_results,
            quality_threshold=args.quality_threshold,
        )

    elif args.approve_all:
        cmd_approve_all(force_refresh=args.refresh)

    elif args.catalog:
        _print_catalog_summary()
        proposed = catalog.list_by_status("proposed")
        if proposed:
            print(f"\n proposed エントリ ({len(proposed)}件):")
            for e in proposed:
                print(f"  [{e.label}] {e.url}")

    elif args.benchmark:
        targets = args.urls or DEFAULT_URLS
        for url in targets:
            try:
                benchmark_url(url, force_refresh=args.refresh)
            except Exception as e:
                print(f"[error] {url}: {e}", file=sys.stderr)

    else:
        targets = args.urls or DEFAULT_URLS
        for url in targets:
            try:
                process_url(url, force_refresh=args.refresh)
            except Exception as e:
                print(f"[error] {url}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
