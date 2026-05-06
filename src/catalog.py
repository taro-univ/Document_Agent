from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import get_args

from src.models import (
    Catalog,
    CatalogEntry,
    CatalogStatus,
    DiscoveryResult,
)

CATALOG_PATH = Path(__file__).parent.parent / "catalog.json"


# ── ファイルI/O ──────────────────────────────────────────────────────────

def load() -> Catalog:
    """catalog.json を読み込んで返す。ファイルが存在しない場合は空のCatalogを返す。"""
    if not CATALOG_PATH.exists():
        return Catalog(last_updated=_today())
    return Catalog.model_validate_json(CATALOG_PATH.read_text(encoding="utf-8"))


def save(catalog: Catalog) -> None:
    """Catalogをcatalog.jsonに保存する。last_updatedを現在日付に更新する。"""
    catalog.last_updated = _today()
    CATALOG_PATH.write_text(
        catalog.model_dump_json(indent=2),
        encoding="utf-8",
    )


# ── 高レベル操作（ロード → 変更 → 保存 → 返す） ─────────────────────────

def add_proposals(result: DiscoveryResult) -> Catalog:
    """DiscoveryResultの proposals を catalog に proposed として追加する。

    既存エントリは上書きせず、新規URLのみ追加する。
    """
    catalog = load()
    added = 0
    for proposal in result.proposals:
        if catalog.find(proposal.url) is not None:
            continue
        catalog.upsert(CatalogEntry(
            url=proposal.url,
            label=proposal.label,
            status="proposed",
            query=result.query,
            last_updated=_today(),
        ))
        added += 1
    save(catalog)
    print(f"[catalog] {added} 件追加 / {len(result.proposals) - added} 件スキップ（重複）")
    return catalog


def approve(urls: list[str]) -> Catalog:
    """指定URLのステータスを approved に更新する。"""
    catalog = load()
    updated = 0
    for url in urls:
        entry = catalog.find(url)
        if entry is None:
            print(f"[catalog] 警告: 未登録のURL → {url}")
            continue
        catalog.upsert(_with_status(entry, "approved"))
        updated += 1
    save(catalog)
    print(f"[catalog] {updated} 件を approved に更新")
    return catalog


def approve_all() -> Catalog:
    """proposed 状態のエントリをすべて approved に更新する。"""
    catalog = load()
    targets = [e for e in catalog.entries if e.status == "proposed"]
    for entry in targets:
        catalog.upsert(_with_status(entry, "approved"))
    save(catalog)
    print(f"[catalog] {len(targets)} 件を approved に更新（approve-all）")
    return catalog


def set_status(
    url: str,
    status: CatalogStatus,
    *,
    local_path: str | None = None,
) -> Catalog:
    """指定URLのstatusを更新する。local_path が渡された場合は同時に更新する。"""
    catalog = load()
    entry = catalog.find(url)
    if entry is None:
        raise KeyError(f"catalog に未登録のURL: {url}")
    updated = _with_status(entry, status, local_path=local_path)
    catalog.upsert(updated)
    save(catalog)
    return catalog


# ── 参照系 ───────────────────────────────────────────────────────────────

def get_labels() -> list[str]:
    """catalog に登録済みのラベル一覧を返す（重複なし・ソート済み）。

    discovery.py の existing_labels として渡すことでラベルの一貫性を保つ。
    """
    catalog = load()
    return sorted({e.label for e in catalog.entries})


def list_by_status(status: CatalogStatus) -> list[CatalogEntry]:
    """指定ステータスのエントリ一覧を返す。"""
    return [e for e in load().entries if e.status == status]


def summary() -> dict[CatalogStatus, int]:
    """ステータスごとの件数を返す。"""
    catalog = load()
    counts: dict[str, int] = {s: 0 for s in get_args(CatalogStatus)}
    for entry in catalog.entries:
        counts[entry.status] += 1
    return counts  # type: ignore[return-value]


# ── 内部ヘルパー ─────────────────────────────────────────────────────────

def _today() -> str:
    return date.today().isoformat()


def _with_status(
    entry: CatalogEntry,
    status: CatalogStatus,
    *,
    local_path: str | None = None,
) -> CatalogEntry:
    """エントリのコピーを作りstatusと last_updated を更新して返す。"""
    data = entry.model_dump()
    data["status"] = status
    data["last_updated"] = _today()
    if local_path is not None:
        data["local_path"] = local_path
    return CatalogEntry(**data)
