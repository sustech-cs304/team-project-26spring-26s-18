"""
???? API ????? Bocha Web Search??
?????BOCHA_API_KEY
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

BOCHA_WEB_SEARCH_URL = "https://api.bochaai.com/v1/web-search"

PLATFORM_DOMAINS: Dict[str, Optional[str]] = {
    "bilibili": "bilibili.com",
    "zhihu": "zhihu.com",
    "csdn": "csdn.net",
    "icourse163": "icourse163.org",
    "mooc": "icourse163.org",
    "baidu": None,
}

PLATFORM_LABELS: Dict[str, str] = {
    "bilibili": "????",
    "zhihu": "??",
    "csdn": "CSDN",
    "icourse163": "????MOOC",
    "mooc": "????MOOC",
    "baidu": "??",
}


def _detect_platform_from_url(url: str) -> str:
    low = (url or "").lower()
    for key, domain in PLATFORM_DOMAINS.items():
        if domain and domain in low:
            return PLATFORM_LABELS.get(key, key)
    return "??"


# ????? API Key?????????
_DEFAULT_BOCHA_API_KEY = "sk-ab71a93c53ff43e7a10bec3a507abb00"


def bocha_web_search(
    query: str,
    *,
    count: int = 5,
    include_domain: Optional[str] = None,
    timeout: float = 25.0,
) -> List[Dict[str, Any]]:
    """
    ???? Web Search API??????????
    ???????? BOCHA_API_KEY????????? Key?
    """
    api_key = os.getenv("BOCHA_API_KEY", _DEFAULT_BOCHA_API_KEY).strip()
    q = (query or "").strip()
    if not api_key or not q:
        return []

    payload: Dict[str, Any] = {
        "query": q,
        "freshness": "noLimit",
        "summary": True,
        "count": min(max(count, 1), 10),
    }
    if include_domain:
        payload["include"] = include_domain

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.post(BOCHA_WEB_SEARCH_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[bocha_web_search] ????: {e}")
        return []

    pages = (data.get("webPages") or {}).get("value") or []
    if not pages and isinstance(data.get("data"), dict):
        pages = (data["data"].get("webPages") or {}).get("value") or []

    out: List[Dict[str, Any]] = []
    for item in pages:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        title = (item.get("name") or item.get("title") or url or "???").strip()
        snippet = (
            item.get("summary")
            or item.get("snippet")
            or item.get("description")
            or ""
        )
        snippet = str(snippet)[:500]
        if not url:
            continue
        platform = _detect_platform_from_url(url)
        site = item.get("siteName") or platform
        out.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": "bocha-serp",
                "platform": site,
                "is_specific_url": True,
            }
        )
    return out
