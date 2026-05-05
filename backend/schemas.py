from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.models import CatalogEntry, DiscoveryProposal

# ── Requests ─────────────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    query: str = Field(description="リサーチクエリ（自然言語）")
    max_results: int = Field(default=10, ge=1, le=20)
    search_provider: Literal["brave", "google"] = "brave"
    quality_threshold: int = Field(default=6, ge=1, le=10)


class ApproveRequest(BaseModel):
    urls: list[str] = Field(description="承認するURLのリスト")


# ── Responses ────────────────────────────────────────────────────────────

class JobResponse(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "error"]
    total: int = Field(description="処理対象の総URL数")
    completed: int = Field(description="抽出完了数")
    failed: list[str] = Field(default_factory=list, description="失敗したURL")


class CatalogResponse(BaseModel):
    entries: list[CatalogEntry]
    total: int


class StatusResponse(BaseModel):
    proposed: int
    approved: int
    fetched: int
    extracted: int
    total: int


class DiscoverResponse(BaseModel):
    proposals: list[DiscoveryProposal]
    rejected: list[DiscoveryProposal]
    added_to_catalog: int = Field(description="新規にcatalogへ追加された件数")


class ResultResponse(BaseModel):
    slug: str
    json_data: dict[str, Any]
    markdown: str
