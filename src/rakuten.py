"""楽天ウェブサービスからトレンド商品・アフィリエイトリンクを取得する。"""

from __future__ import annotations

import random
from dataclasses import dataclass

import requests

from . import config

RANKING_API = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
SEARCH_API = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"


@dataclass
class Product:
    name: str
    price: int
    url: str  # アフィリエイトURL
    genre_id: str
    genre_name: str
    review_average: float
    review_count: int
    catchcopy: str


def _base_params() -> dict:
    if not config.RAKUTEN_APPLICATION_ID:
        raise RuntimeError("RAKUTEN_APPLICATION_ID が設定されていません(.env を確認)")
    params = {
        "applicationId": config.RAKUTEN_APPLICATION_ID,
        "format": "json",
    }
    if config.RAKUTEN_AFFILIATE_ID:
        params["affiliateId"] = config.RAKUTEN_AFFILIATE_ID
    return params


def _to_product(item: dict, genre_id: str, genre_name: str) -> Product:
    return Product(
        name=item.get("itemName", ""),
        price=int(item.get("itemPrice", 0)),
        # affiliateId を渡していれば affiliateUrl が返る
        url=item.get("affiliateUrl") or item.get("itemUrl", ""),
        genre_id=genre_id,
        genre_name=genre_name,
        review_average=float(item.get("reviewAverage", 0) or 0),
        review_count=int(item.get("reviewCount", 0) or 0),
        catchcopy=item.get("catchcopy", ""),
    )


def fetch_trending(genre_id: str, limit: int = 10) -> list[Product]:
    """指定ジャンルのランキング上位(=いま売れているトレンド商品)を取得。"""
    params = _base_params()
    params["genreId"] = genre_id
    resp = requests.get(RANKING_API, params=params, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("Items", [])[:limit]
    genre_name = config.MOM_GENRES.get(genre_id, "")
    return [_to_product(entry["Item"], genre_id, genre_name) for entry in items]


def search_products(keyword: str, limit: int = 10) -> list[Product]:
    """キーワードで商品検索(レビュー件数順=定番人気)。"""
    params = _base_params()
    params.update({"keyword": keyword, "sort": "-reviewCount", "hits": limit})
    resp = requests.get(SEARCH_API, params=params, timeout=30)
    resp.raise_for_status()
    items = resp.json().get("Items", [])
    return [_to_product(entry["Item"], "", keyword) for entry in items]


def pick_product(preferred_genres: list[str] | None = None) -> Product:
    """おすすめ商品を1つ自動選定する。

    バズ分析で成績のよかったジャンル(preferred_genres)を優先し、
    ランキング上位のうちレビュー評価4.0以上・レビュー100件以上から選ぶ。
    """
    genre_pool = preferred_genres or list(config.MOM_GENRES.keys())
    random.shuffle(genre_pool)
    for genre_id in genre_pool:
        try:
            products = fetch_trending(genre_id, limit=15)
        except requests.RequestException:
            continue
        good = [p for p in products if p.review_average >= 4.0 and p.review_count >= 100]
        if good:
            return random.choice(good[:8])
        if products:
            return random.choice(products[:5])
    raise RuntimeError("商品を取得できませんでした(楽天APIの設定を確認してください)")
