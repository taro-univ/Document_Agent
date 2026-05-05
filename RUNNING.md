# サービス起動手順

## ディレクトリ構成の確認

すべてのコマンドは **プロジェクトルート** (`Document_agent/`) を基点として説明します。

```
Document_agent/       ← ここがプロジェクトルート
├── .venv/            ← Python 仮想環境（バックエンド用）
├── backend/
├── frontend/         ← Next.js（npm で管理）
└── src/
```

> **注意**: `frontend/` の中にいる状態でバックエンドを起動しようとすると  
> `no such file or directory: .venv/bin/uvicorn` エラーが出ます。  
> バックエンドは必ずプロジェクトルートから起動してください。

---

## 初回セットアップ

### 1. Python 仮想環境のセットアップ（バックエンド）

```bash
cd ~/Document_agent

# 仮想環境を有効化
source .venv/bin/activate

# 依存パッケージをインストール（初回のみ）
pip install -r requirements.txt
```

### 2. フロントエンドのセットアップ（初回のみ）

```bash
cd ~/Document_agent/frontend
npm install
```

### 3. 環境変数の設定

プロジェクトルートの `.env` に以下のキーを設定します。

```bash
# ~/Document_agent/.env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=github_pat_...
BRAVE_API_KEY=BSA...          # Discovery機能に必要
OPENAI_API_KEY=sk-proj-...    # ベンチマーク機能を使う場合
```

---

## サービスの起動

**ターミナルを2つ**開いて、それぞれで起動します。

### ターミナル 1 — バックエンド（FastAPI）

```bash
# プロジェクトルートに移動（重要）
cd ~/Document_agent

# 仮想環境を有効化
source .venv/bin/activate

# サーバー起動
.venv/bin/uvicorn backend.main_api:app --port 8000 --reload
```

起動確認: `http://localhost:8000/docs` にアクセスして Swagger UI が表示されれば OK。

### ターミナル 2 — フロントエンド（Next.js）

```bash
# frontend ディレクトリに移動
cd ~/Document_agent/frontend

# 開発サーバー起動
npm run dev
```

起動確認: `http://localhost:3000` にアクセスして画面が表示されれば OK。

---

## アクセス先

| サービス | URL | 用途 |
|---|---|---|
| フロントエンド | http://localhost:3000 | Discovery・Catalog・結果ビューア |
| API ドキュメント | http://localhost:8000/docs | Swagger UI（API の直接テスト） |
| バックエンド API | http://localhost:8000/api/... | REST エンドポイント |

---

## CLI での操作（フロントエンドを使わない場合）

バックエンドを起動せず、CLI から直接操作することもできます。

```bash
cd ~/Document_agent
source .venv/bin/activate

# Web検索 → LLM評価 → catalog登録
python -m src.main --discover "GitHub Copilot pricing 2026"

# 提案されたURLを全件承認して抽出
python -m src.main --approve-all

# catalog の現在の状態を確認
python -m src.main --catalog

# デフォルトURLリストを直接抽出
python -m src.main
```

---

## よくあるエラー

### `no such file or directory: .venv/bin/uvicorn`

**原因**: `frontend/` など別ディレクトリからコマンドを実行している。  
**対処**: `cd ~/Document_agent` でプロジェクトルートに移動してから実行。

### `ModuleNotFoundError: No module named 'src'`

**原因**: プロジェクトルート以外から `python -m src.main` を実行している。  
**対処**: `cd ~/Document_agent` でプロジェクトルートに移動してから実行。

### `EnvironmentError: BRAVE_API_KEY が未設定です`

**原因**: `.env` に `BRAVE_API_KEY` が設定されていない。  
**対処**: `.env` を開いて `BRAVE_API_KEY=...` を記入。  
取得先: https://api.search.brave.com/app/keys

### バックエンドに接続できない（フロントエンドからの通信エラー）

**原因**: バックエンドが起動していない、またはポート 8000 が使用中。  
**対処**:
```bash
# バックエンドが起動しているか確認
curl http://localhost:8000/api/status

# ポート 8000 を使用しているプロセスを確認
lsof -i :8000
```
