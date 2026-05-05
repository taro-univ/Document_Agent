from __future__ import annotations

import os
import time
from typing import Literal

import anthropic
import instructor
import openai
from dotenv import load_dotenv

from src.models import BenchmarkEntry, BenchmarkReport, DocumentExtraction

load_dotenv()

Provider = Literal["anthropic", "openai", "github_models"]

# プロバイダーごとのデフォルトモデル名
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-3-5-sonnet-latest",
    "openai": "gpt-4o",
    "github_models": "gpt-4o",
}

# GitHub Models のベースURL（OpenAI SDK互換）
_GITHUB_MODELS_BASE_URL = "https://models.inference.ai.azure.com"

_SYSTEM_PROMPT = """\
あなたはGitHubの公式ドキュメントを解析する技術情報抽出エキスパートです。

以下の指針に従って抽出してください：
- 事実のみを抽出し、推測は含めないこと
- 情報が存在しない場合は「記載なし」と明示すること
- 2026年6月移行前後の仕様は必ず区別すること
- C/C++, Rust, RTOS, MCU, Embedded Systems に関する言及は優先的に抽出すること
- namespaceは「Copilot」または「Models」のいずれかを判定して設定すること
"""

# Pass 2 専用: 補完コンテンツを使って空欄を埋めることに特化した追加指示
_PASS2_SYSTEM_PROMPT = """\
あなたはGitHubの公式ドキュメントを解析する技術情報抽出エキスパートです。

今回は「Pass 2（補完フェーズ）」です。以下の指針に従ってください：
- 事実のみを抽出し、推測は含めないこと
- コンテンツには複数のソースページが含まれます（<!-- SOURCE: URL --> で区切られています）
- 特に以下のフィールドを重点的に埋めてください：
  * ai_models: モデル名を具体的に列挙（例: GPT-4o, Claude 3.5 Sonnet, Llama 3等）
  * supported_ecosystems: 言語・IDE・フレームワーク（例: Python, C++, VS Code, JetBrains）
  * interface_tools: CLIコマンド名・拡張機能名（例: gh copilot, VS Code Extension）
  * commands_scripts: そのままコピペできるコマンド例（例: gh copilot suggest "..."）
  * custom_agents: .agent.md やMCP連携の記述があれば抽出
- namespaceは「Copilot」または「Models」のいずれかを判定して設定すること
- 情報が存在しない場合のみ「記載なし」と記載すること
"""


def get_client(provider: Provider):
    """指定プロバイダーの instructor クライアントを返す。"""
    if provider == "anthropic":
        return instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        )
    elif provider == "openai":
        return instructor.from_openai(
            openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        )
    elif provider == "github_models":
        return instructor.from_openai(
            openai.OpenAI(
                api_key=os.environ["GITHUB_TOKEN"],
                base_url=_GITHUB_MODELS_BASE_URL,
            )
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")


def extract(
    url: str,
    content: str,
    provider: Provider = "anthropic",
    model: str | None = None,
    is_pass2: bool = False,
) -> DocumentExtraction:
    """クリーン済みMarkdownコンテンツからDocumentExtractionを生成して返す。

    is_pass2=True の場合は補完フェーズ用プロンプトを使用する。
    """
    client = get_client(provider)
    model_name = model or _DEFAULT_MODELS[provider]
    system = _PASS2_SYSTEM_PROMPT if is_pass2 else _SYSTEM_PROMPT

    user_content = (
        f"以下はURL: {url} およびその補完ページから取得したドキュメントです。\n\n"
        f"---\n{content}\n---\n\n"
        "DocumentExtractionスキーマに従い情報を抽出してください。"
    )

    kwargs: dict = dict(
        max_tokens=4096,
        messages=[{"role": "user", "content": user_content}],
        response_model=DocumentExtraction,
    )

    if provider == "anthropic":
        kwargs["system"] = system
        kwargs["model"] = model_name
        return client.chat.completions.create(**kwargs)
    else:
        kwargs["model"] = model_name
        kwargs["messages"].insert(0, {"role": "system", "content": system})
        return client.chat.completions.create(**kwargs)


def benchmark(
    url: str,
    content: str,
    providers: list[tuple[Provider, str | None]] | None = None,
) -> BenchmarkReport:
    """複数プロバイダーで同一コンテンツを抽出し、BenchmarkReportを返す。"""
    if providers is None:
        providers = [
            ("anthropic", None),
            ("openai", None),
            ("github_models", None),
        ]

    entries: list[BenchmarkEntry] = []
    for provider, model in providers:
        model_name = model or _DEFAULT_MODELS[provider]
        print(f"  [benchmark] {provider} / {model_name}")
        t0 = time.perf_counter()
        result = extract(url, content, provider=provider, model=model_name)
        elapsed = time.perf_counter() - t0
        entries.append(
            BenchmarkEntry(
                provider=provider,
                model_name=model_name,
                elapsed_sec=round(elapsed, 2),
                extraction=result,
            )
        )

    return BenchmarkReport(url=url, entries=entries)
