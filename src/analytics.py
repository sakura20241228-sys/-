"""バズ分析: 過去投稿のインサイトを集計し、次の投稿戦略を決める。"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from . import store, threads_client


def refresh_all_metrics() -> int:
    """全投稿のインサイトをThreads APIから取り直して保存。更新件数を返す。"""
    updated = 0
    for entry in store.load_history():
        try:
            metrics = threads_client.get_insights(entry["media_id"])
            store.update_metrics(entry["media_id"], metrics)
            updated += 1
        except Exception:
            continue
    return updated


def _engagement(metrics: dict | None) -> float:
    """エンゲージメントスコア(いいね・返信・リポストを重み付けし閲覧数も加味)。"""
    if not metrics:
        return 0.0
    return (
        metrics.get("likes", 0) * 3
        + metrics.get("replies", 0) * 5
        + metrics.get("reposts", 0) * 4
        + metrics.get("quotes", 0) * 4
        + metrics.get("views", 0) * 0.01
    )


def best_genres(top_n: int = 3) -> list[str]:
    """エンゲージメントが高かった順にジャンルIDを返す(データ不足なら空)。"""
    scores: dict[str, list[float]] = defaultdict(list)
    for entry in store.load_history():
        if entry["post_type"] == "affiliate" and entry.get("genre_id"):
            scores[entry["genre_id"]].append(_engagement(entry.get("metrics")))
    ranked = sorted(scores.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True)
    return [genre_id for genre_id, vals in ranked[:top_n] if sum(vals) > 0]


def top_posts(top_n: int = 3) -> list[dict]:
    """バズった(スコア上位の)投稿を返す。投稿文生成のお手本に使う。"""
    history = [e for e in store.load_history() if e.get("metrics")]
    history.sort(key=lambda e: _engagement(e["metrics"]), reverse=True)
    return history[:top_n]


def summary() -> str:
    """人が読むための簡易レポート。"""
    history = store.load_history()
    if not history:
        return "まだ投稿履歴がありません。"
    lines = [f"総投稿数: {len(history)}"]
    with_metrics = [e for e in history if e.get("metrics")]
    if with_metrics:
        total_views = sum(e["metrics"].get("views", 0) for e in with_metrics)
        total_likes = sum(e["metrics"].get("likes", 0) for e in with_metrics)
        lines.append(f"累計閲覧数: {total_views} / 累計いいね: {total_likes}")
    genres = best_genres()
    if genres:
        from . import config

        names = [config.MOM_GENRES.get(g, g) for g in genres]
        lines.append(f"伸びているジャンル: {', '.join(names)}")
    for i, post in enumerate(top_posts(3), 1):
        views = (post.get("metrics") or {}).get("views", 0)
        likes = (post.get("metrics") or {}).get("likes", 0)
        excerpt = post["text"][:40].replace("\n", " ")
        lines.append(f"バズ{i}位: [{views}views/{likes}likes] {excerpt}…")
    return "\n".join(lines)
