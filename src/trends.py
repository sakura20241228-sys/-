"""話題のトピック取得。GoogleトレンドとGoogleニュースのRSSから今日の話題を拾う。

取得に失敗しても投稿は止めない(generator側で内蔵トピックにフォールバックする)。
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote

import requests

# 日本の急上昇ワード
GOOGLE_TRENDS_RSS = "https://trends.google.co.jp/trending/rss?geo=JP"

# ママ向けの話題をニュース検索で拾うキーワード
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja"
NEWS_QUERIES = ["子育て", "育児", "育休"]

_TIMEOUT = 15
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; threads-autopost/1.0)"}


def _fetch_rss_titles(url: str, limit: int) -> list[str]:
    resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    titles = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def _clean(title: str) -> str:
    # Googleニュースのタイトル末尾「 - 媒体名」を落とす
    return re.sub(r"\s+-\s+[^-]+$", "", title).strip()


def trending_topics(limit: int = 12) -> list[str]:
    """今日の話題の候補リストを返す。取得できなければ空リスト。"""
    topics: list[str] = []

    try:
        topics += _fetch_rss_titles(GOOGLE_TRENDS_RSS, 5)
    except Exception:
        pass

    for query in NEWS_QUERIES:
        try:
            titles = _fetch_rss_titles(GOOGLE_NEWS_RSS.format(query=quote(query)), 3)
            topics += [_clean(t) for t in titles]
        except Exception:
            pass

    # 重複を除去(順序は保つ)
    seen: set[str] = set()
    unique = []
    for t in topics:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:limit]
