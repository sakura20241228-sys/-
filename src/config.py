"""設定の読み込み。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "post_history.json"
INSIGHTS_FILE = DATA_DIR / "insights.json"

RAKUTEN_APPLICATION_ID = os.getenv("RAKUTEN_APPLICATION_ID", "")
RAKUTEN_AFFILIATE_ID = os.getenv("RAKUTEN_AFFILIATE_ID", "")

THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# 子育てママ向けの楽天ジャンル(genreId は楽天市場の公式ジャンルID)
MOM_GENRES = {
    "100533": "キッズ・ベビー・マタニティ",
    "558929": "おもちゃ",
    "100227": "食品",
    "558944": "日用品雑貨・文房具・手芸",
    "100804": "インテリア・寝具・収納",
    "551177": "スイーツ・お菓子",
    "100939": "美容・コスメ・香水",
}

# アフィリエイト投稿と日常投稿の比率(daily 1 に対して affiliate N)
# 例: 2 なら「アフィ2回に1回は日常投稿」。1 なら交互
AFFILIATE_TO_DAILY_RATIO = 1

# ステマ規制(2023年10月〜)対応: アフィリエイト投稿に必ず付ける表記
PR_LABEL = "#PR"
