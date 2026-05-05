# Document Intelligence Agent

GitHub の公式ドキュメント・テックブログ・APIリファレンスを自動収集・構造化するフルスタックエージェント。

Web 検索から LLM による情報抽出・評価まで一貫したパイプラインを備え、CLI と Web UI の両方から操作できます。

---

## 主な機能

| 機能 | 概要 |
|---|---|
| **Discovery** | Brave / Google Search API で関連ページを検索し、LLM がノイズを除去して採用候補を提案 |
| **Human-in-the-loop** | 提案リストをユーザーが確認・承認してから抽出を実行 |
| **2パス抽出** | Pass 1 で基本抽出 → 空欄フィールドを検出 → Pass 2 で補完ページを追加取得して再抽出 |
| **構造化出力** | Pydantic スキーマに準拠した JSON と Markdown を同時生成 |
| **マルチプロバイダー** | Anthropic / OpenAI / GitHub Models を切り替え可能、ベンチマーク比較にも対応 |
| **Catalog 管理** | `proposed → approved → fetched → extracted` のステータスで URL のライフサイクルを管理 |

---

## アーキテクチャ

```
ユーザー入力（クエリ）
        │
        ▼
┌─────────────────┐     Brave / Google
│  discovery.py   │ ──→ Search API
│  検索 & LLM評価  │ ──→ セマンティック・ゲートキーパー（品質スコア算出）
└────────┬────────┘
         │ DiscoveryProposal リスト
         ▼
  Human-in-the-loop（承認）
         │
         ▼
┌─────────────────┐
│  scraper.py     │  httpx + BeautifulSoup4 + markdownify
│  HTML → MD変換  │  キャッシュあり（MD5ベース、べき等性確保）
└────────┬────────┘
         │
    ┌────▼─────────────────────────────┐
    │           2パス抽出               │
    │  Pass 1: メインページ抽出          │
    │  ↓ 空欄フィールド検出             │
    │  Pass 2: 補完ページ追加 → 再抽出   │
    │  ↓ フィールド単位でマージ          │
    └────┬─────────────────────────────┘
         │ DocumentExtraction (Pydantic)
         ▼
┌─────────────────┐
│  catalog.py     │  JSON ステータス管理（catalog.json）
│  results/       │  data/output/*.json + *.md
└─────────────────┘
```

---

## 技術スタック

**バックエンド**
- Python 3.12 / FastAPI / uvicorn
- [instructor](https://github.com/instructor-ai/instructor) — LLM レスポンスを Pydantic モデルに強制マッピング
- httpx / BeautifulSoup4 / markdownify — スクレイピングパイプライン
- Anthropic SDK / OpenAI SDK — マルチプロバイダー対応

**フロントエンド**
- Next.js 16 (App Router) / TypeScript / Tailwind CSS
- SWR — データフェッチ & ジョブポーリング

---

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-username/document-intelligence-agent.git
cd document-intelligence-agent
```

### 2. 環境変数の設定

```bash
cp .env.example .env
# .env を開いて各 API キーを記入
```

必須キー:

| キー | 用途 | 取得先 |
|---|---|---|
| `ANTHROPIC_API_KEY` | LLM による抽出 | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `GITHUB_TOKEN` | GitHub Models 経由の推論 | [github.com/settings/tokens](https://github.com/settings/tokens) |
| `BRAVE_API_KEY` | Web 検索（Discovery 機能） | [api.search.brave.com](https://api.search.brave.com/app/keys) |

### 3. Python 環境のセットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 4. フロントエンドのセットアップ

```bash
cd frontend
npm install
```

---

## 起動方法

ターミナルを2つ開いて起動します。

```bash
# ターミナル 1 — バックエンド（プロジェクトルートから）
source .venv/bin/activate
uvicorn backend.main_api:app --port 8000 --reload

# ターミナル 2 — フロントエンド
cd frontend && npm run dev
```

| サービス | URL |
|---|---|
| Web UI | http://localhost:3000 |
| API ドキュメント | http://localhost:8000/docs |

---

## 使い方

### Web UI

1. **Discovery 画面**（`/`）でリサーチクエリを入力
2. LLM が評価した採用候補リストを確認
3. 気になる候補の **Approve & Extract** をクリック
4. **Catalog 画面**（`/catalog`）でステータスを確認
5. `extracted` になったら **View Result** で結果を閲覧

### CLI

```bash
# Web検索 → LLM評価 → catalog登録
python -m src.main --discover "GitHub Copilot pricing 2026"

# 提案を全承認して抽出
python -m src.main --approve-all

# catalog の状態確認
python -m src.main --catalog

# 複数モデルでベンチマーク比較
python -m src.main --benchmark
```

---

## 出力フォーマット

抽出結果は `data/output/` に JSON と Markdown の2形式で保存されます。

```json
{
  "product_name": "GitHub Copilot",
  "namespace": "Copilot",
  "billing": {
    "billing_model": "従量制",
    "plans_available": ["Free", "Pro", "Pro+", "Business", "Enterprise"],
    "usage_limits": "1 AI credit = $0.01 USD"
  },
  "tech_spec": {
    "ai_models": ["GPT-4o", "Claude Sonnet 4.6", "Gemini 2.5 Pro", ...],
    "supported_ecosystems": ["C", "C++", "Rust", "Python", ...]
  },
  "timeline": {
    "current": "リクエストベース課金",
    "post_june_2026": "GitHub AI Credits ベースの従量制に移行"
  }
}
```

---

## プロジェクト構成

```
.
├── src/
│   ├── main.py          # CLI エントリポイント
│   ├── discovery.py     # 検索 & LLM セマンティック評価
│   ├── scraper.py       # HTML 取得・クリーンアップ・キャッシュ
│   ├── extractor.py     # instructor による構造化抽出（2パス）
│   ├── catalog.py       # catalog.json の読み書き管理
│   └── models.py        # Pydantic スキーマ定義
├── backend/
│   ├── main_api.py      # FastAPI アプリ
│   └── schemas.py       # Request / Response モデル
├── frontend/
│   ├── app/             # Next.js App Router
│   ├── components/      # UI コンポーネント
│   ├── lib/api.ts       # API クライアント
│   └── types/           # TypeScript 型定義
├── data/
│   ├── raw/             # スクレイプキャッシュ（gitignore）
│   └── output/          # 抽出済み JSON / Markdown（gitignore）
├── .env.example
├── requirements.txt
└── RUNNING.md           # 起動手順の詳細
```

---

## ライセンス

MIT
