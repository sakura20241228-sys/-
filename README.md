# 楽天アフィリエイト × Threads(スレッズ)自動運用ツール

子育てママ・育休ママ向けアカウントを想定した、楽天アフィリエイトのThreads自動運用ツールです。

## できること

| 機能 | 内容 |
|---|---|
| 🛒 商品の自動サーチ | 楽天ランキングAPIから「ベビー・キッズ」「食品」「日用品」などママ向けジャンルのトレンド商品を自動選定(レビュー4.0以上・100件以上を優先) |
| ✍️ 投稿文の自動生成 | Claude AIがママ向けの自然な話し言葉で投稿文を作成。ステマ規制対応の「#PR」も自動付与 |
| ☕ 日常投稿ミックス | アフィ投稿ばかりにならないよう、育児あるあるなどの雑談投稿を自動で混ぜる(比率は設定可能・初期設定は交互) |
| 📰 話題のトピック連動 | GoogleトレンドとGoogleニュース(子育て・育児・育休)から今日の話題を自動取得し、育休ママ・育児ママの共感を呼ぶ日常投稿に反映。事件・政治などアカウントに合わない話題はAIが自動でスキップ |
| 🍼 育休ママ向けトピック | 「育休中の孤独感」「職場復帰の不安」「保活」など育休ママの定番ネタ+月ごとの季節ネタを内蔵(トレンドが取れない時のフォールバックにも使用) |
| 📈 バズ分析 | 過去投稿の閲覧数・いいね・リポストをThreads APIから取得。伸びたジャンルを次の商品選定に、バズった投稿の文体を次の文章生成に自動反映 |
| 🤖 完全自動運用 | GitHub Actionsで毎日3回(朝・昼・夜)自動投稿+週1で自動分析 |

## セットアップ

### 1. 必要なアカウント・キーを用意

1. **楽天ウェブサービス** … <https://webservice.rakuten.co.jp/> でアプリ登録 → 「アプリID」を取得
2. **楽天アフィリエイト** … <https://affiliate.rakuten.co.jp/> → 「アフィリエイトID」を確認
3. **Threads API** … <https://developers.facebook.com/> でアプリ作成(Threadsユースケース)→ 長期アクセストークンとユーザーIDを取得
4. **Claude API(任意)** … <https://platform.claude.com/> でAPIキー取得。なくてもテンプレート文で動きます

### 2. ローカルで試す

```bash
pip install -r requirements.txt
cp .env.example .env   # 各キーを記入

# まずは投稿せずに内容を確認(おすすめ)
python main.py post --dry-run

# 実際に投稿
python main.py post

# バズ分析
python main.py analyze
```

### 3. 自動運用(GitHub Actions)

GitHubリポジトリの **Settings → Secrets and variables → Actions** に以下を登録すると、毎日 7:30 / 12:30 / 20:30(日本時間)に自動投稿されます。

- `RAKUTEN_APPLICATION_ID`
- `RAKUTEN_AFFILIATE_ID`
- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`
- `ANTHROPIC_API_KEY`(任意)

投稿時間は `.github/workflows/autopost.yml` の cron(UTC表記)で変更できます。

## カスタマイズ

`src/config.py` で調整できます。

- `MOM_GENRES` … 商品をサーチする楽天ジャンル
- `AFFILIATE_TO_DAILY_RATIO` … アフィ投稿と日常投稿の比率(初期設定は `1` = 交互)
- `src/generator.py` の `SYSTEM_PROMPT` … 投稿文のトーンやルール
- `src/generator.py` の `DAILY_TOPICS` / `SEASONAL_TOPICS` … 日常投稿の定番ネタ・季節ネタ
- `src/trends.py` の `NEWS_QUERIES` … 話題を拾うニュース検索キーワード

## ⚠️ 運用上の注意

- **ステマ規制(景品表示法)**: アフィリエイト投稿には広告であることの表示が必須です。本ツールは自動で「#PR」を付けますが、削除しないでください。
- **Threadsの自動化ポリシー**: 過度な連続投稿はアカウント制限の対象になり得ます。1日3回程度に留める設定にしています。
- **楽天アフィリエイト規約**: リンクの改変や虚偽の商品説明は規約違反です。投稿前に `--dry-run` で内容確認する運用をおすすめします。
- Threadsのアクセストークン(長期)は約60日で失効します。定期的に更新してください。
