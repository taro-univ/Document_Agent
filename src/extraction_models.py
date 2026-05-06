from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


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


class BenchmarkEntry(BaseModel):
    provider: str = Field(description="プロバイダー名 (anthropic / openai / github_models)")
    model_name: str = Field(description="使用したモデル名")
    elapsed_sec: float = Field(description="抽出にかかった秒数")
    extraction: DocumentExtraction


class BenchmarkReport(BaseModel):
    url: str
    entries: list[BenchmarkEntry]
