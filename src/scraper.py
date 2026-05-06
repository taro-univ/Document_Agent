from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DocumentAgent/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

_REMOVE_TAGS = ["nav", "header", "footer", "aside", "script", "style", "noscript"]

_SUPPLEMENT_URLS_PATH = Path(__file__).parent.parent / "supplement_urls.json"

# URLスラッグ → Pass 2 で追加取得する補完ページ
# 設定は supplement_urls.json で管理。ファイルがなければ空dict。
SUPPLEMENT_URLS: dict[str, list[str]] = (
    json.loads(_SUPPLEMENT_URLS_PATH.read_text(encoding="utf-8"))
    if _SUPPLEMENT_URLS_PATH.exists()
    else {}
)


def slug_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _url_to_cache_path(url: str) -> Path:
    digest = hashlib.md5(url.encode()).hexdigest()[:12]
    return RAW_DIR / f"{digest}.md"


def fetch_and_clean(url: str, *, force_refresh: bool = False) -> str:
    """URLからHTMLを取得し、Markdown形式のクリーンなテキストを返す。キャッシュあり。"""
    cache_path = _url_to_cache_path(url)

    if cache_path.exists() and not force_refresh:
        return cache_path.read_text(encoding="utf-8")

    response = httpx.get(url, headers=_HEADERS, follow_redirects=True, timeout=30)
    response.raise_for_status()

    clean_md = _html_to_markdown(response.text)
    cache_path.write_text(clean_md, encoding="utf-8")
    return clean_md


def fetch_supplements(url: str, *, force_refresh: bool = False) -> str | None:
    """補完URLリストを取得して結合したコンテンツを返す。補完URLがなければNoneを返す。"""
    slug = slug_from_url(url)
    supplement_urls = SUPPLEMENT_URLS.get(slug)
    if not supplement_urls:
        return None

    parts: list[str] = []
    for sup_url in supplement_urls:
        try:
            content = fetch_and_clean(sup_url, force_refresh=force_refresh)
            parts.append(f"<!-- SOURCE: {sup_url} -->\n{content}")
            print(f"  [supplement] {sup_url}")
        except Exception as e:
            print(f"  [supplement skip] {sup_url}: {e}")

    return "\n\n---\n\n".join(parts) if parts else None


def _html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in _REMOVE_TAGS:
        for element in soup.find_all(tag):
            element.decompose()

    main = soup.find("main") or soup.find("article") or soup.body
    content_html = str(main) if main else html

    return md(content_html, heading_style="ATX", strip=["a"])
