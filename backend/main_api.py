from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import src.catalog as catalog_module
from src.discovery import discover
from src.main import process_url
from src.scraper import slug_from_url

from backend.schemas import (
    ApproveRequest,
    CatalogResponse,
    DiscoverRequest,
    DiscoverResponse,
    JobResponse,
    ResultResponse,
    StatusResponse,
)

load_dotenv()

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "output"

app = FastAPI(
    title="Document Intelligence Agent API",
    version="1.0.0",
    description="GitHub ドキュメント解析エージェントのREST API",
)

_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── インメモリ ジョブストア ────────────────────────────────────────────────
# 値は JobResponse と同じ構造の dict。FastAPI がレスポンス時に検証する。
_jobs: dict[str, dict] = {}


# ── エンドポイント ────────────────────────────────────────────────────────

@app.get("/api/catalog", response_model=CatalogResponse)
def get_catalog():
    """全カタログエントリを返す。"""
    cat = catalog_module.load()
    return CatalogResponse(entries=cat.entries, total=len(cat.entries))


@app.get("/api/status", response_model=StatusResponse)
def get_status():
    """ステータス別の件数サマリーを返す。"""
    s = catalog_module.summary()
    return StatusResponse(**s, total=sum(s.values()))


@app.post("/api/discover", response_model=DiscoverResponse)
def post_discover(body: DiscoverRequest):
    """クエリで検索 → LLM評価 → catalog登録。採用/却下リストを返す。"""
    existing_labels = catalog_module.get_labels() or None
    result = discover(
        body.query,
        max_results=body.max_results,
        search_provider=body.search_provider,
        existing_labels=existing_labels,
        quality_threshold=body.quality_threshold,
    )
    catalog_module.add_proposals(result)
    return DiscoverResponse(
        proposals=result.proposals,
        rejected=result.rejected,
        added_to_catalog=len(result.proposals),
    )


@app.post("/api/approve", response_model=JobResponse)
def post_approve(body: ApproveRequest, background_tasks: BackgroundTasks):
    """指定URLを個別承認し、バックグラウンドで抽出ジョブを開始する。"""
    if not body.urls:
        raise HTTPException(status_code=400, detail="urls が空です")

    missing = [u for u in body.urls if catalog_module.load().find(u) is None]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"catalog に未登録のURL: {missing}",
        )

    catalog_module.approve(body.urls)
    job_id = _create_job(len(body.urls))
    background_tasks.add_task(_run_extraction, job_id, body.urls)
    return _jobs[job_id]


@app.post("/api/approve-all", response_model=JobResponse)
def post_approve_all(background_tasks: BackgroundTasks):
    """proposed を全承認し、バックグラウンドで抽出ジョブを開始する。"""
    proposed = catalog_module.list_by_status("proposed")
    if not proposed:
        raise HTTPException(status_code=400, detail="proposed なエントリがありません")

    catalog_module.approve_all()
    urls = [e.url for e in proposed]
    job_id = _create_job(len(urls))
    background_tasks.add_task(_run_extraction, job_id, urls)
    return _jobs[job_id]


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    """ジョブのステータスをポーリング用に返す。"""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail=f"job_id '{job_id}' が存在しません")
    return _jobs[job_id]


@app.get("/api/results/{slug}", response_model=ResultResponse)
def get_result(slug: str):
    """抽出済みドキュメントのJSON + Markdownを返す。"""
    json_path = OUTPUT_DIR / f"{slug}.json"
    md_path = OUTPUT_DIR / f"{slug}.md"

    if not json_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"'{slug}' の抽出結果が見つかりません。先に抽出を実行してください。",
        )

    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    return ResultResponse(slug=slug, json_data=json_data, markdown=markdown)


# ── ジョブ管理 ────────────────────────────────────────────────────────────

def _create_job(total: int) -> str:
    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "total": total,
        "completed": 0,
        "failed": [],
    }
    return job_id


def _run_extraction(job_id: str, urls: list[str]) -> None:
    """BackgroundTasks から呼ばれる同期関数。FastAPI がスレッドプールで実行する。"""
    _jobs[job_id]["status"] = "running"
    for url in urls:
        try:
            json_path = process_url(url)
            slug = slug_from_url(url)
            catalog_module.set_status(
                url,
                "extracted",
                local_path=f"data/output/{slug}.json",
            )
            _jobs[job_id]["completed"] += 1
        except Exception as e:
            print(f"[job/{job_id}] error {url}: {e}")
            _jobs[job_id]["failed"].append(url)

    _jobs[job_id]["status"] = "done" if not _jobs[job_id]["failed"] else "error"
