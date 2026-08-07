"""Threads(スレッズ)公式APIクライアント。投稿とインサイト取得。"""

from __future__ import annotations

import time

import requests

from . import config

API_BASE = "https://graph.threads.net/v1.0"


def _check_credentials() -> None:
    if not (config.THREADS_ACCESS_TOKEN and config.THREADS_USER_ID):
        raise RuntimeError(
            "THREADS_ACCESS_TOKEN / THREADS_USER_ID が設定されていません(.env を確認)"
        )


def post_text(text: str) -> str:
    """テキスト投稿を作成・公開し、投稿IDを返す。"""
    _check_credentials()
    # 1. コンテナ作成
    resp = requests.post(
        f"{API_BASE}/{config.THREADS_USER_ID}/threads",
        data={
            "media_type": "TEXT",
            "text": text,
            "access_token": config.THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # 公式ドキュメント推奨: 公開前に少し待つ
    time.sleep(5)

    # 2. 公開
    resp = requests.post(
        f"{API_BASE}/{config.THREADS_USER_ID}/threads_publish",
        data={
            "creation_id": creation_id,
            "access_token": config.THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def get_insights(media_id: str) -> dict:
    """投稿1件のインサイト(閲覧数・いいね等)を取得。"""
    _check_credentials()
    resp = requests.get(
        f"{API_BASE}/{media_id}/insights",
        params={
            "metric": "views,likes,replies,reposts,quotes",
            "access_token": config.THREADS_ACCESS_TOKEN,
        },
        timeout=30,
    )
    resp.raise_for_status()
    metrics = {}
    for entry in resp.json().get("data", []):
        values = entry.get("values", [{}])
        metrics[entry["name"]] = values[0].get("value", 0) if values else 0
    return metrics
