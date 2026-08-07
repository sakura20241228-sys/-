"""投稿履歴・インサイトのJSON保存。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config


def _load(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history() -> list[dict]:
    return _load(config.HISTORY_FILE)


def record_post(
    media_id: str,
    text: str,
    post_type: str,
    genre_id: str = "",
    genre_name: str = "",
    product_name: str = "",
) -> None:
    history = load_history()
    history.append(
        {
            "media_id": media_id,
            "text": text,
            "post_type": post_type,  # "affiliate" or "daily"
            "genre_id": genre_id,
            "genre_name": genre_name,
            "product_name": product_name,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "metrics": None,
        }
    )
    _save(config.HISTORY_FILE, history)


def update_metrics(media_id: str, metrics: dict) -> None:
    history = load_history()
    for entry in history:
        if entry["media_id"] == media_id:
            entry["metrics"] = metrics
            entry["metrics_updated_at"] = datetime.now(timezone.utc).isoformat()
    _save(config.HISTORY_FILE, history)


def recent_post_types(n: int = 5) -> list[str]:
    """直近n件の投稿タイプ(affiliate/daily)を新しい順で返す。"""
    history = load_history()
    return [e["post_type"] for e in reversed(history[-n:])]


def recent_product_names(n: int = 20) -> set[str]:
    """直近で紹介した商品名(重複紹介を避けるため)。"""
    history = load_history()
    return {e["product_name"] for e in history[-n:] if e.get("product_name")}
