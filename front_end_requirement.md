# Frontend Requirements
> FastAPI + Next.js による Document Intelligence Agent のフルスタック実装要件

---

## 技術スタック

| レイヤー | 技術 | 選定理由 |
|---|---|---|
| Backend API | FastAPI | 既存Pythonコードをそのまま利用可能 |
| Frontend | Next.js (App Router) + TypeScript | 現在の標準構成 |
| UI | Tailwind CSS + shadcn/ui | 軽量・コピペ対応、カスタマイズ容易 |
| データフェッチ | SWR | ポーリングのビルトインサポートが手軽 |

---

## 1. ディレクトリ構造

```
Document_agent/
├── backend/
│   ├── __init__.py
│   ├── main_api.py        # FastAPIアプリ本体
│   └── schemas.py         # Request / Response Pydanticモデル
├── frontend/
│   ├── app/
│   │   ├── page.tsx               # Discovery画面（トップ）
│   │   ├── catalog/
│   │   │   └── page.tsx           # Catalog一覧画面
│   │   └── results/
│   │       └── [slug]/
│   │           └── page.tsx       # 抽出結果ビューア
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── ProposalCard.tsx       # 採用候補カード
│   │   ├── RejectedList.tsx       # 却下リスト（折りたたみ）
│   │   ├── CatalogCard.tsx        # Catalogエントリカード
│   │   ├── StatusBadge.tsx        # proposed / approved / extracted バッジ
│   │   ├── MarkdownViewer.tsx     # 抽出済みMD表示
│   │   └── JobStatusPoller.tsx    # 抽出進捗ポーリング
│   ├── lib/
│   │   └── api.ts                 # APIクライアント関数
│   └── types/
│       └── index.ts               # 共有型定義
├── src/                           # 既存バックエンド（変更なし）
├── catalog.json
└── requirements.txt
```

---

## 2. Backend Implementation (FastAPI)

`backend/main_api.py` を作成し、既存の `catalog.py` / `discovery.py` / `main.py` のロジックをラップします。

### エンドポイント一覧

| Method | Path | 概要 |
|---|---|---|
| `GET` | `/api/catalog` | 全エントリ一覧を返す |
| `GET` | `/api/status` | ステータス別の件数サマリーを返す |
| `POST` | `/api/discover` | クエリで検索・LLM評価・catalog登録。採用/却下リストを返す |
| `POST` | `/api/approve` | 指定URLを個別承認し、抽出ジョブを開始。`job_id` を返す |
| `POST` | `/api/approve-all` | proposed を全承認し、抽出ジョブを開始。`job_id` を返す |
| `GET` | `/api/jobs/{job_id}` | ジョブのステータス（running / done / error）をポーリング用に返す |
| `GET` | `/api/results/{slug}` | 抽出済みドキュメントのJSON + Markdownを返す |

### 非同期抽出の設計（ジョブIDパターン）

`process_url()` は30〜60秒かかるため、レスポンスを即返してバックグラウンドで処理します。

```
1. POST /api/approve  →  { "job_id": "abc123" } を即返す
2. BackgroundTasks で process_url() を実行
3. 完了時にジョブストアのステータスを更新
4. GET /api/jobs/abc123  →  { "status": "running" | "done" | "error", "urls": [...] }
```

ジョブストアはサーバーメモリ上の辞書（`dict[str, JobStatus]`）で実装します（初期実装としてはシンプルさを優先）。

### `backend/schemas.py` で定義するモデル

```python
# Request
class DiscoverRequest(BaseModel):
    query: str
    max_results: int = 10
    search_provider: str = "brave"
    quality_threshold: int = 6

class ApproveRequest(BaseModel):
    urls: list[str]

# Response
class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    total: int
    completed: int
    failed: list[str] = []
```

### 設定事項

- **CORS**: `localhost:3000` からのリクエストを許可
- **catalog.json のパス**: `backend/` から見た相対パスで `Path(__file__).parent.parent / "catalog.json"` を参照（フロントエンドは直接読まない）

---

## 3. Frontend Implementation (Next.js App Router)

### ページ構成

#### `/` — Discovery画面（トップ）

**表示要素:**
- `SearchBar`: クエリ入力 → `POST /api/discover`
- `ProposalCard` リスト: 採用候補を score の高い順にカード表示
  - スコアバー・ラベル・URL・採用理由を表示
  - 個別 **Approve** ボタン → `POST /api/approve`
- `RejectedList`: 却下リストを折りたたみで表示（却下理由付き）
- `JobStatusPoller`: 承認後に `GET /api/jobs/{job_id}` をポーリングし進捗バーを表示

#### `/catalog` — Catalog一覧画面

**表示要素:**
- ステータス別フィルタタブ（All / proposed / approved / extracted）
- `CatalogCard` リスト: 各エントリをカード形式で表示
  - `StatusBadge`: ステータスに応じて色分け（proposed=灰 / approved=青 / extracted=緑）
  - proposed カードには **Approve** ボタンを表示
  - extracted カードには **View Result** リンクを表示
- **Approve All** ボタン → `POST /api/approve-all`

#### `/results/[slug]` — 結果ビューア

**表示要素:**
- `MarkdownViewer`: `GET /api/results/{slug}` から取得したMarkdownをレンダリング
- JSONアコーディオン: 生のJSONデータを折りたたみ表示
- メタ情報ヘッダー: `product_name` / `namespace` / `last_updated` / `source_url`

### コンポーネント詳細

```
SearchBar.tsx
  - 入力中はボタンをdisabled
  - 検索中はスピナー表示
  - エラー時はトースト通知

ProposalCard.tsx
  - Props: DiscoveryProposal
  - スコアをプログレスバーで表示（/10）
  - Approveボタン押下後: ボタンをローディング状態に変更

RejectedList.tsx
  - デフォルト折りたたみ（クリックで展開）
  - 件数バッジのみ常時表示

JobStatusPoller.tsx
  - job_id を受け取り、2秒間隔でポーリング
  - done になったらカタログを再フェッチして終了
  - error 時はトースト通知

StatusBadge.tsx
  - status に応じて色を変える
  - proposed: gray / approved: blue / fetched: yellow / extracted: green
```

### `frontend/lib/api.ts` — APIクライアント

```typescript
const BASE = "http://localhost:8000"

export const api = {
  getCatalog:  () => fetch(`${BASE}/api/catalog`).then(r => r.json()),
  getStatus:   () => fetch(`${BASE}/api/status`).then(r => r.json()),
  discover:    (body: DiscoverRequest) => fetch(`${BASE}/api/discover`, { method: "POST", ... }),
  approve:     (urls: string[]) => fetch(`${BASE}/api/approve`, { method: "POST", ... }),
  approveAll:  () => fetch(`${BASE}/api/approve-all`, { method: "POST" }).then(r => r.json()),
  getJob:      (jobId: string) => fetch(`${BASE}/api/jobs/${jobId}`).then(r => r.json()),
  getResult:   (slug: string) => fetch(`${BASE}/api/results/${slug}`).then(r => r.json()),
}
```

---

## 4. 実行手順

```bash
# Backend 起動
uvicorn backend.main_api:app --port 8000 --reload

# Frontend 起動（別ターミナル）
cd frontend && npm run dev
```

アクセス先:
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`（FastAPIの自動生成ドキュメント）

---

## 5. 実装優先順位

| 優先度 | タスク |
|---|---|
| 🔴 高 | `backend/schemas.py` + `backend/main_api.py` の基本エンドポイント |
| 🔴 高 | ジョブIDパターンの実装（approve → job_id → polling） |
| 🔴 高 | `/` Discovery画面 + `SearchBar` + `ProposalCard` |
| 🟡 中 | `/catalog` 一覧画面 + `StatusBadge` + `CatalogCard` |
| 🟡 中 | `JobStatusPoller`（進捗フィードバック） |
| 🟡 中 | `/results/[slug]` MarkdownViewer |
| 🟢 低 | `RejectedList` の折りたたみUI |
| 🟢 低 | エラー・ローディングスケルトンの整備 |
