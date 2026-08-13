"""楽天アフィリエイト × Threads 自動運用ツール

使い方:
  python main.py post            # 投稿を1件自動生成して投稿(アフィ/日常を自動で判断)
  python main.py post --dry-run  # 投稿せず内容の確認だけ
  python main.py post --type affiliate  # アフィリエイト投稿を強制
  python main.py post --type daily      # 日常投稿を強制
  python main.py analyze         # 過去投稿のインサイトを取得してバズ分析レポート表示
  python main.py copy            # 集客用の投稿文の下書きを作成(全訴求タイプ1案ずつ)
  python main.py copy --theme 寝かしつけ --appeal 共感 --count 3
"""

from __future__ import annotations

import argparse
import sys

from src import analytics, config, copywriter, generator, rakuten, store, threads_client


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


def cmd_copy(theme: str | None, appeal: str | None, count: int, save: bool) -> None:
    results = copywriter.make_drafts(theme, appeal, count)
    print(f"=== テーマ: {results[0]['theme']} ===\n")
    for i, r in enumerate(results, 1):
        role = copywriter.APPEALS[r["appeal"]]["役割"]
        print(f"--- 案{i}【{r['appeal']}】{role} ---")
        print(r["text"])
        ng = copywriter.ng_words_in(r["text"])
        if ng:
            print(f"⚠️ NGワードが含まれています: {'、'.join(ng)} → 言い換えてから投稿してください")
        print()
    theme = results[0]["theme"]
    print("✍️ 書く前にノートに書き出してみる問いかけ:")
    for q in copywriter.idea_questions(theme):
        print(f"  ・{q}")
    print()
    if save:
        path = copywriter.save_drafts(results)
        print(f"下書きを保存しました: {path}")
    if not config.ANTHROPIC_API_KEY:
        print("※ ANTHROPIC_API_KEY 未設定のため穴埋め式テンプレートです。(…)の部分を埋めて使ってください。")


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

    p_copy = sub.add_parser("copy", help="集客用の投稿文の下書きを作成")
    p_copy.add_argument("--theme", default=None, help="テーマ(例: 寝かしつけ)。省略時はおすすめテーマから自動選択")
    p_copy.add_argument(
        "--appeal",
        choices=list(copywriter.APPEALS),
        default=None,
        help="訴求タイプ。省略時は全タイプ1案ずつ作成",
    )
    p_copy.add_argument("--count", type=int, default=3, help="--appeal指定時の案数(既定: 3)")
    p_copy.add_argument("--save", action="store_true", help="data/drafts.md に下書きを保存")

    sub.add_parser("analyze", help="インサイト取得とバズ分析")

    args = parser.parse_args()
    try:
        if args.command == "post":
            cmd_post(args.type, args.dry_run)
        elif args.command == "copy":
            cmd_copy(args.theme, args.appeal, args.count, args.save)
        elif args.command == "analyze":
            cmd_analyze()
    except RuntimeError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
