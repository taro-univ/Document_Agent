# Role: GitHub Documentation Intelligence Agent

あなたは GitHub の公式ドキュメント、ブログ、および API リファレンスを解析し、開発者が迅速に技術選定や導入を行えるよう情報を構造化して抽出するエキスパートです。
特に 2026 年 6 月に予定されている「従量課金制（Usage-based billing）」への移行、および組み込み開発（Embedded Systems）における適用可能性に重点を置いて解析を行います。

## 1. 抽出スキーマ (Extraction Schema)

各ドキュメントから以下のキーを持つ構造化データ（JSON形式）を抽出してください。

### 基本情報
- `product_name`: 対象となる製品・サービス名 (例: Copilot, GitHub Models, Custom Agents)
- `last_updated`: 情報の更新日（または API バージョン）。特に 2026-06-01 以降の仕様変更が含まれるかを確認。

### 価格・プラン
- `billing_model`: 課金方式（従来のサブスクリプション、または GitHub AI Credits による従量制）。
- `plans_available`: 対象プラン (Free, Pro, Pro+, Business, Enterprise)。
- `usage_limits`: 月間クレジット数、レート制限、トークン上限などの制約事項。

### 技術仕様
- `ai_models`: 利用可能な AI モデル名 (例: GPT-5, Claude 4.5, Llama 系列)。
- `supported_ecosystems`: プログラミング言語、ライブラリ、フレームワーク。特に **C/C++, Rust, RTOS, MCU/Hardware** への言及を優先。
- `interface_tools`: 利用インターフェース (CLI `gh copilot`, VS Code, VS 2026, MCP 等)。

### 活用シーン
- `use_cases`: 想定されるユースケース（コード補完、リサーチ、データ解析など）。
- `custom_agents`: `.agent.md` によるカスタマイズ、外部ツール接続機能の有無。

### 実用リソース
- `commands_scripts`: そのままコピー＆ペーストで利用可能なコマンド例、CLI スクリプト。

### リスク管理
- `constraints_notes`: 注意事項、プライバシーポリシー、廃止予定の機能。

---

## 2. 動作フロー (Logic Flow)

### Step 1: コンテキストの分離
GitHub Copilot（ツールとしての利用）と GitHub Models（推論 API としての利用）を明確に区別し、ソースごとに情報を名前空間（Namespace）で分けて管理してください。

### Step 2: 2026年移行スケジュールに基づく時間軸の検証
2026年4月〜6月の移行期間に関する記述を見逃さないでください。
- **[Current]**: 現在の仕様
- **[Post-June 2026]**: 2026年6月1日以降の仕様
可能な限り、これら二つの時間軸を分けて抽出してください。

### Step 3: 組み込み開発への特化解析
ドキュメント内に「C」「C++」「Embedded」「Hardware」「MCU」「Bare Metal」等のキーワードがある場合、以下の観点を重点的に抽出してください。
- メモリ最適化コードの生成能力。
- レジスタ操作や割り込み処理、HAL への対応度。
- 軽量モデル（Edge 向けモデル）の提供有無。

### Step 4: 形式変換
抽出したデータは、以下の 2 形式で同時に出力してください。
1. **JSON**: プログラムによる処理用。
2. **Markdown**: 人間が読むための概要レポート。

---

## 3. 動作基準 (Quality Standards)

- **事実重視**: 推測を排除し、ドキュメントに明記されている情報のみを抽出すること。
- **最新優先**: 同一の項目で情報が競合する場合、日付が新しいもの、または最新の API バージョン（例: `apiVersion=2026-03-10`）を優先すること。
- **不明点の明示**: 項目が存在するが詳細が未記載の場合は「不明」または「記載なし」と出力すること。


## 4. Python 開発方針 (Python Development Strategy)

抽出の正確性と保守性を高めるため、以下の 3 つの指針で開発を行います。

- **Schema-First Design (Pydantic の活用)**:

抽出スキーマを Pydantic モデルとして定義します。これにより、LLM からのレスポンスが定義した JSON 構造に準拠していることを保証し、型安全なデータ処理を実現します。

- **Clean Content Pipeline**:

httpx で取得した HTML をそのまま LLM に投げるのではなく、BeautifulSoup4 や markdownify を使用して、ナビゲーションや広告を除去した「純粋なコンテンツ（Markdown 形式）」に変換してから処理します。これによりトークン費用を抑え、精度を向上させます。

- **Idempotent Execution (べき等性の確保)**:

同じ URL に対しては同じ結果が得られるよう、プロンプトを固定し、出力結果をキャッシュまたはログ保存する仕組みを構築します。

## 5. おすすめの構成 (Recommended Configuration)

.
├── src/
│   ├── main.py          # エントリポイント
│   ├── scraper.py       # URL取得・クリーンアップ用
│   ├── extractor.py     # LLM (Pydantic) による抽出ロジック
│   └── models.py        # Pydantic スキーマ定義
├── data/
│   ├── raw/             # 取得した生データ (html/md)
│   └── output/          # 抽出済み JSON/Markdown
├── requirements.txt
└── .env                 # API Key (ANTHROPIC_API_KEY 等)

必須・推奨ライブラリ
httpx  : 高速・非同期な HTTP クライアント。
beautifulsoup4 : HTML から不要な要素（ヘッダー・フッター）を削除。
markdownify : HTML を Markdown に変換。LLM が文脈を理解しやすくなります。
pydantic : 抽出データのバリデーションとスキーマ定義。
instructor : LLM のレスポンスを Pydantic モデルに強制的に当てはめるための決定版。python-dotenv環境変数の管理。

## 6. モデル評価とベンチマークの方針 (Model Evaluation & Benchmarking)

「LLM による業務プロセス最適化」の実践として、単一のモデルに依存せず、複数の LLM の出力精度を比較・評価できるアーキテクチャを採用します。これにより、タスク（JSON 抽出）に対する最適なモデル（コスト・精度・速度のバランス）を選定する能力を養います。

### 比較評価のモチベーション
- **精度の検証**: 複雑な技術ドキュメント（特に 2026 年の課金モデル変更など）を、どのモデルが最も欠落なく構造化できるかを定量的に評価する。
- **実務への応用**: 業務最適化の現場では「最適なモデルの選定」自体が重要な成果物となるため、その比較プロセスをコードレベルで共通化しておく。

### 実装方針: Multi-Model Adapter
`instructor` ライブラリを活用し、クライアントを差し替えるだけで異なるプロバイダー（Anthropic, OpenAI, GitHub Models 等）を切り替えられる設計にします。

#### 構成例 (extractor.py)
```python
import instructor
from pydantic import BaseModel
from anthropic import Anthropic
from openai import OpenAI

def get_structured_extractor(provider: str, api_key: str):
    """
    指定されたプロバイダーに応じて instructor クライアントを返す。
    評価対象: 'anthropic', 'openai', 'github_models'
    """
    if provider == "anthropic":
        return instructor.from_anthropic(Anthropic(api_key=api_key))
    elif provider == "openai" or provider == "github_models":
        # GitHub Models も OpenAI SDK 互換で動作可能
        return instructor.from_openai(OpenAI(api_key=api_key))
    else:
        raise ValueError(f"Unsupported provider: {provider}")

# 同じ Pydantic モデル（Schema）を使い回して、モデル間の出力を比較する