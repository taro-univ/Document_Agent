from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

# ──────────────────────────────────────────────
# Discovery パイプライン用モデル
# ──────────────────────────────────────────────

class DiscoverySignals(BaseModel):
    """セマンティック・ゲートキーパーによる品質評価結果。"""

    is_technical_resource: bool = Field(
        description="技術的な一次情報かどうか（アフィリエイト・SEOゴミを排除）"
    )
    quality_score: int = Field(
        ge=1, le=10,
        description="技術的信頼度スコア (1=最低, 10=最高)"
    )
    positive_signals: list[str] = Field(
        default_factory=list,
        description="採用理由（公式ドメイン・バージョン明記・コード片あり等）",
    )
    negative_signals: list[str] = Field(
        default_factory=list,
        description="減点理由（煽り文句・仕様なし・古い情報等）",
    )


class DiscoveryProposal(BaseModel):
    """検索結果1件に対するLLMの評価・提案。Human-in-the-loop の承認単位。"""

    url: str = Field(description="候補URL")
    title: str = Field(description="ページタイトル")
    snippet: str = Field(description="検索結果のスニペット（評価の根拠）")
    label: str = Field(
        description=(
            "動的ラベル。既存ラベルに寄せるか、新概念なら汎用名を生成。"
            "例: api_reference, pricing_2026, github_copilot/benchmarks"
        )
    )
    signals: DiscoverySignals
    reasoning: str = Field(description="採用・却下の判断根拠（1〜2文）")

    @field_validator("label")
    @classmethod
    def label_lowercase(cls, v: str) -> str:
        return v.lower().replace(" ", "_")


class DiscoveryResult(BaseModel):
    """1クエリから得られた提案・却下リストのまとめ。ユーザーへの提示単位。"""

    query: str = Field(description="元のリサーチクエリ")
    proposals: list[DiscoveryProposal] = Field(description="承認候補（quality_score >= 閾値）")
    rejected: list[DiscoveryProposal] = Field(
        default_factory=list,
        description="却下済み（is_technical_resource=False または低スコア）",
    )

    @property
    def approved_urls(self) -> list[str]:
        return [p.url for p in self.proposals]


# catalog.json の status 遷移: proposed → approved → fetched → extracted
CatalogStatus = Literal["proposed", "approved", "fetched", "extracted"]


class CatalogEntry(BaseModel):
    """catalog.json の1エントリ。URLのライフサイクルを管理する。"""

    url: str
    label: str
    status: CatalogStatus = "proposed"
    local_path: Optional[str] = Field(
        default=None, description="data/raw/ 以下の保存パス（fetch後に設定）"
    )
    query: Optional[str] = Field(
        default=None, description="このURLを発見した元クエリ"
    )
    last_updated: str = Field(description="最終更新日 (YYYY-MM-DD)")


class Catalog(BaseModel):
    """catalog.json 全体のスキーマ。"""

    last_updated: str
    entries: list[CatalogEntry] = Field(default_factory=list)

    def find(self, url: str) -> Optional[CatalogEntry]:
        return next((e for e in self.entries if e.url == url), None)

    def upsert(self, entry: CatalogEntry) -> None:
        existing = self.find(entry.url)
        if existing:
            self.entries[self.entries.index(existing)] = entry
        else:
            self.entries.append(entry)


# ──────────────────────────────────────────────
# 既存モデル（DocumentExtraction 系）
# ──────────────────────────────────────────────


class BenchmarkEntry(BaseModel):
    provider: str = Field(description="プロバイダー名 (anthropic / openai / github_models)")
    model_name: str = Field(description="使用したモデル名")
    elapsed_sec: float = Field(description="抽出にかかった秒数")
    extraction: "DocumentExtraction"


class BenchmarkReport(BaseModel):
    url: str
    entries: list[BenchmarkEntry]


class BillingInfo(BaseModel):
    billing_model: str = Field(description="課金方式（サブスクリプション or 従量制）")
    plans_available: list[str] = Field(description="対象プラン例: [Free, Pro, Business, Enterprise]")
    usage_limits: str = Field(description="月間クレジット数・レート制限・トークン上限など")


class TechSpec(BaseModel):
    ai_models: list[str] = Field(description="利用可能なAIモデル名")
    supported_ecosystems: list[str] = Field(
        description="対応言語・ライブラリ・フレームワーク。C/C++/Rust/MCU関連を優先"
    )
    interface_tools: list[str] = Field(description="利用インターフェース（CLI, VS Code, MCP等）")


class UseCaseInfo(BaseModel):
    use_cases: list[str] = Field(description="想定ユースケース")
    custom_agents: str = Field(description=".agent.mdによるカスタマイズや外部ツール接続の有無")


class TimelineEntry(BaseModel):
    current: str = Field(description="現行仕様")
    post_june_2026: str = Field(description="2026年6月1日以降の仕様")


class DocumentExtraction(BaseModel):
    # 基本情報
    product_name: str = Field(description="対象製品・サービス名")
    namespace: str = Field(description="Copilot または Models")
    last_updated: str = Field(description="情報の更新日またはAPIバージョン")
    source_url: str = Field(description="取得元URL")

    # 価格・プラン
    billing: BillingInfo

    # 技術仕様
    tech_spec: TechSpec

    # 活用シーン
    use_case_info: UseCaseInfo

    # 実用リソース
    commands_scripts: list[str] = Field(description="コピペ可能なコマンド例・CLIスクリプト")

    # リスク管理
    constraints_notes: list[str] = Field(description="注意事項・プライバシーポリシー・廃止予定機能")

    # 移行スケジュール
    timeline: Optional[TimelineEntry] = Field(
        default=None, description="2026年移行に関する現行/移行後の仕様"
    )

    # 組み込み開発特化情報（該当する場合のみ）
    embedded_relevance: Optional[str] = Field(
        default=None,
        description="組み込み開発（メモリ最適化・レジスタ操作・HAL等）への対応度",
    )
