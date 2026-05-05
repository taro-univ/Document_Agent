from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.extractor import Provider, _DEFAULT_MODELS, get_client
from src.models import DiscoveryProposal, DiscoveryResult

load_dotenv()

# ── 定数 ────────────────────────────────────────────────────────────────
_BRAVE_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
_GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

DEFAULT_MAX_RESULTS = 10
DEFAULT_QUALITY_THRESHOLD = 6  # quality_score がこれ未満 or is_technical_resource=False → 却下

SearchProvider = Literal["brave", "google"]


# ── 内部型（検索APIの生レスポンスを保持するだけ、LLM非関与） ────────────
@dataclass
class _RawResult:
    url: str
    title: str
    snippet: str


# ── instructor がマッピングする内部モデル ────────────────────────────────
class _EvaluationOutput(BaseModel):
    """LLMが全件評価した結果リスト。採用・却下の分類はPython側で行う。"""

    items: list[DiscoveryProposal] = Field(
        description="全検索結果の評価済みリスト（採用・却下どちらも含む）"
    )


# ── ゲートキーパープロンプト ─────────────────────────────────────────────
_GATEKEEPER_SYSTEM_PROMPT = """\
あなたは高度な技術リサーチャーです。
与えられた検索結果を評価し、研究ライブラリに保存する価値があるかを判定してください。

## 採点基準

### Positive Signals（加点）
- ドメインが公式サイト（docs.*, blog.openai.com, github.com/openai 等）
- 具体的なバージョン番号（v3.5, 2026-03-10 等）やコード片を含む
- API仕様・スキーマ・ベンチマーク・破壊的変更など技術的具体性がある
- 2026年現在の最新情報（課金モデル変更・新モデル等）に言及している

### Negative Signals（減点・即排除）
- 「完全ガイド」「おすすめ」「〜選」など一般消費者向けの煽り文句
- 具体的仕様なしの価格比較・メリデメ羅列
- 明らかに古い情報（スニペットが2023年以前で新情報なし）
- アフィリエイト・SEO目的の薄いコンテンツ

## quality_score の目安
- 9〜10: 公式ドキュメント・公式ブログで仕様が明記されている
- 7〜8 : 信頼できる技術ブログ・カンファレンス資料で具体的情報あり
- 5〜6 : 参考になるが一次情報でない、または情報の鮮度が低い
- 1〜4 : SEOゴミ・広告・古い情報・一般向け概要のみ

## ラベリングルール
- 既存ラベルに寄せられる場合は既存ラベルを優先
- 全く新しい概念の場合のみ新設（英小文字 + アンダースコア形式）
- 製品名含む場合: product_name/category 形式（例: github_copilot/pricing）
- 時系列重要な場合: category_YYYY 形式（例: pricing_2026）

## 出力ルール
- 全件を評価して items に含めること（採用・却下どちらも）
- reasoning は1〜2文で判断根拠を明記すること
"""


# ── 検索APIラッパー ──────────────────────────────────────────────────────

def _search_brave(query: str, max_results: int) -> list[_RawResult]:
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key or api_key == "your_brave_api_key_here":
        raise EnvironmentError(
            "BRAVE_API_KEY が未設定です。.env に設定してください。\n"
            "取得先: https://api.search.brave.com/app/keys"
        )
    resp = httpx.get(
        _BRAVE_ENDPOINT,
        headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        params={"q": query, "count": min(max_results, 20), "search_lang": "en"},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("web", {}).get("results", [])
    return [
        _RawResult(url=r["url"], title=r["title"], snippet=r.get("description", ""))
        for r in results
    ]


def _search_google(query: str, max_results: int) -> list[_RawResult]:
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    cse_id = os.environ.get("GOOGLE_CSE_ID", "")
    if not api_key or api_key == "your_google_api_key_here":
        raise EnvironmentError(
            "GOOGLE_API_KEY / GOOGLE_CSE_ID が未設定です。.env に設定してください。"
        )
    resp = httpx.get(
        _GOOGLE_ENDPOINT,
        params={"key": api_key, "cx": cse_id, "q": query, "num": min(max_results, 10)},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        _RawResult(url=r["link"], title=r["title"], snippet=r.get("snippet", ""))
        for r in items
    ]


def search(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    provider: SearchProvider = "brave",
) -> list[_RawResult]:
    """指定の検索APIでクエリを実行し、生の検索結果を返す。"""
    if provider == "brave":
        return _search_brave(query, max_results)
    if provider == "google":
        return _search_google(query, max_results)
    raise ValueError(f"Unsupported search provider: {provider}")


# ── LLMによるセマンティック評価 ──────────────────────────────────────────

def evaluate(
    query: str,
    raw_results: list[_RawResult],
    existing_labels: list[str] | None = None,
    quality_threshold: int = DEFAULT_QUALITY_THRESHOLD,
    provider: Provider = "github_models",
    model: str | None = None,
) -> DiscoveryResult:
    """LLMで検索結果を一括評価し、採用/却下に分類したDiscoveryResultを返す。"""
    client = get_client(provider)
    model_name = model or _DEFAULT_MODELS[provider]

    labels_context = (
        f"既存ラベル（可能な限り再利用すること）: {', '.join(existing_labels)}"
        if existing_labels
        else "既存ラベル: なし（新規プロジェクト）"
    )

    results_text = "\n\n".join(
        f"[{i + 1}]\nURL: {r.url}\nTitle: {r.title}\nSnippet: {r.snippet}"
        for i, r in enumerate(raw_results)
    )

    user_content = (
        f"## リサーチクエリ\n{query}\n\n"
        f"## {labels_context}\n\n"
        f"## 検索結果（{len(raw_results)}件）\n\n{results_text}\n\n"
        "全件を評価し、DiscoveryProposal 形式で items リストに返してください。"
    )

    kwargs: dict = dict(
        max_tokens=4096,
        messages=[{"role": "user", "content": user_content}],
        response_model=_EvaluationOutput,
    )

    if provider == "anthropic":
        kwargs["system"] = _GATEKEEPER_SYSTEM_PROMPT
        kwargs["model"] = model_name
    else:
        kwargs["model"] = model_name
        kwargs["messages"].insert(0, {"role": "system", "content": _GATEKEEPER_SYSTEM_PROMPT})

    output: _EvaluationOutput = client.chat.completions.create(**kwargs)

    # Python側でスコアに基づいて採用/却下を分類
    proposals = [
        p for p in output.items
        if p.signals.is_technical_resource and p.signals.quality_score >= quality_threshold
    ]
    rejected = [
        p for p in output.items
        if not (p.signals.is_technical_resource and p.signals.quality_score >= quality_threshold)
    ]

    return DiscoveryResult(query=query, proposals=proposals, rejected=rejected)


# ── メインエントリーポイント ─────────────────────────────────────────────

def discover(
    query: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    search_provider: SearchProvider = "brave",
    llm_provider: Provider = "github_models",
    existing_labels: list[str] | None = None,
    quality_threshold: int = DEFAULT_QUALITY_THRESHOLD,
) -> DiscoveryResult:
    """検索 → LLMセマンティック評価 のパイプラインを実行する。

    Args:
        query:              自然言語のリサーチクエリ
        max_results:        検索API取得件数（Brave: 最大20, Google: 最大10）
        search_provider:    検索API ("brave" or "google")
        llm_provider:       評価LLMプロバイダー
        existing_labels:    catalog.json の既存ラベル一覧（ラベル一貫性のため）
        quality_threshold:  採用とみなす quality_score の下限（デフォルト6）
    """
    print(f"[search]   '{query}' via {search_provider} (max={max_results})")
    raw = search(query, max_results=max_results, provider=search_provider)
    print(f"[search]   {len(raw)} 件取得")

    print(f"[evaluate] {llm_provider} で評価中...")
    result = evaluate(
        query,
        raw,
        existing_labels=existing_labels,
        quality_threshold=quality_threshold,
        provider=llm_provider,
    )
    print(
        f"[evaluate] 採用: {len(result.proposals)} 件 / "
        f"却下: {len(result.rejected)} 件 "
        f"(threshold={quality_threshold})"
    )
    return result
