"""楽天アフィリエイト × Threads 自動運用ツール

使い方:
  python main.py post            # 投稿を1件自動生成して投稿(アフィ/日常を自動で判断)
  python main.py post --dry-run  # 投稿せず内容の確認だけ
  python main.py post --type affiliate  # アフィリエイト投稿を強制
  python main.py post --type daily      # 日常投稿を強制
  python main.py analyze         # 過去投稿のインサイトを取得してバズ分析レポート表示
"""

from __future__ import annotations

import argparse
import sys

from src import analytics, config, generator, rakuten, store, threads_client


def decide_post_type() -> str:
    """直近の投稿履歴から、次はアフィか日常かを決める。"""
    recent = store.recent_post_types(config.AFFILIATE_TO_DAILY_RATIO)
    if recent and all(t == "affiliate" for t in recent):
        return "daily"
    return "affiliate"


def cmd_post(post_type: str | None, dry_run: bool) -> None:
    post_type = post_type or decide_post_type()

    if post_type == "affiliate":
        preferred = analytics.best_genres()  # バズ分析の結果を商品選定に反映
        recent_names = store.recent_product_names()
        product = rakuten.pick_product(preferred)
        for _ in range(5):  # 直近に紹介した商品は避ける
            if product.name not in recent_names:
                break
            product = rakuten.pick_product(preferred)
        text = generator.affiliate_post(product)
        meta = {
            "genre_id": product.genre_id,
            "genre_name": product.genre_name,
            "product_name": product.name,
        }
    else:
        text = generator.daily_post()
        meta = {}

    print(f"--- 投稿タイプ: {post_type} ---")
    print(text)
    print("-" * 30)

    if dry_run:
        print("(dry-run: 投稿はしていません)")
        return

    media_id = threads_client.post_text(text)
    store.record_post(media_id, text, post_type, **meta)
    print(f"投稿しました! media_id={media_id}")


def cmd_analyze() -> None:
    print("インサイトを取得中…")
    updated = analytics.refresh_all_metrics()
    print(f"{updated}件の投稿の指標を更新しました。\n")
    print(analytics.summary())


def main() -> None:
    parser = argparse.ArgumentParser(description="楽天アフィリエイト × Threads 自動運用")
    sub = parser.add_subparsers(dest="command", required=True)

    p_post = sub.add_parser("post", help="投稿を自動生成して投稿")
    p_post.add_argument("--type", choices=["affiliate", "daily"], default=None)
    p_post.add_argument("--dry-run", action="store_true", help="投稿せず内容確認だけ")

    sub.add_parser("analyze", help="インサイト取得とバズ分析")

    args = parser.parse_args()
    try:
        if args.command == "post":
            cmd_post(args.type, args.dry_run)
        elif args.command == "analyze":
            cmd_analyze()
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
