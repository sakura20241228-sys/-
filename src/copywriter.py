"""集客用のThreads投稿文づくりを手伝うツール。

育児ママ向けに自分のサービス・商品へ集客したいアカウントのための
下書きジェネレーター。

  python main.py copy                       # 全訴求タイプ1案ずつ
  python main.py copy --theme 寝かしつけ     # テーマ指定
  python main.py copy --appeal 共感 --count 3  # 訴求タイプ指定で3案

Claude APIキーがあれば完成形の投稿文を、なければ穴埋め式の
構成テンプレート(そのまま埋めれば投稿できる形)を出力する。

訴求の方向性を変えたいときは:
- src/config.py の BUSINESS_PROFILE にサービス情報を記入
- このファイルの PRINCIPLES(訴求ルール10か条)と APPEALS を調整
"""

from __future__ import annotations

import datetime
import random
import textwrap

from . import analytics, config, generator

MAX_LENGTH = 480  # Threadsの上限500文字に余裕を持たせる

# 集客アカウントで反応を取りやすいテーマ(--theme 省略時にここから選ぶ)
# 前半: 動画編集×在宅ワーク系(集客の本命テーマ)
# 後半: 育児あるある系(共感でフォロワーを増やすテーマ)
THEMES = [
    "動画編集の始め方",
    "ママの在宅ワーク",
    "スキマ時間の使い方",
    "子育てしながら働く",
    "パソコン苦手の克服",
    "ママの副業選び",
    "寝かしつけ",
    "イヤイヤ期",
    "ワンオペ育児",
    "自分時間がない",
]

# ===== 訴求ルール10か条(すべての投稿文に共通で適用) =====
# AI生成時はこのままプロンプトに入る。テンプレートもこの構成に沿っている。
PRINCIPLES = textwrap.dedent("""\
    ① 1行目に「常識と逆の言葉(ギャップ)」を入れる
    ② 「えっ?どういうこと?」でスクロールの手を止める
    ③ ノウハウ説明じゃなく「読者がキュンとする未来」を見せる
    ④ 過去の自分が悩んでいた頃の「本音の願い」を思い出す
    ⑤ 「〜するだけ♡」という手軽さ・ラクさを言葉に乗せる
    ⑥ どこかの丸写しじゃなく「自分がやってるリアルな工夫」を渡す
    ⑦ ノートを開いて「普段どうやってる?」を自分に問いかける
    ⑧ 「大事にしているポイント(こだわり)」もセットで書く
    ⑨ 綺麗にまとめず「60点のリアルな自分」をそのまま書く
    ⑩ 複雑さを手放して「あなただけの切り口」で届ける""")

# ①のギャップ1行目の型(テンプレートのヒント・AI生成の参考に使う)
GAP_HOOK_EXAMPLES = [
    "{theme}、頑張るのやめました。",
    "{theme}、実は「ちゃんとやらない」方がうまくいきます。",
    "{theme}が苦手なママほど、うまくいくって知ってました?",
    "{theme}のコツ、調べるのやめたら解決しました。",
    "ズボラな私ほど{theme}がラクになった話。",
]

# 動画編集×在宅ワーク系のテーマのときだけ使う型
WORK_HOOK_EXAMPLES = [
    "パソコン苦手だった私が、動画編集をお仕事にできた理由。",
    "動画編集、センスは要りませんでした。",
    "「ママだから働けない」って、思い込みでした。",
    "資格ゼロ・経験ゼロの私が選んだのは、動画編集でした。",
]

# テーマにこの言葉が入っていたら「お仕事系テーマ」とみなす
WORK_KEYWORDS = ["動画", "編集", "在宅", "副業", "働", "仕事", "パソコン", "スキマ", "収入"]


def _hook_candidates(theme: str) -> list[str]:
    hooks = [h.format(theme=theme) for h in GAP_HOOK_EXAMPLES]
    if any(k in theme for k in WORK_KEYWORDS):
        hooks += WORK_HOOK_EXAMPLES
    return hooks

# ④⑦のための「書く前の問いかけ」(ノートに書き出す用)
IDEA_QUESTIONS = [
    "普段、{theme}を自分はどうやってる?(ノートに書き出してみる)",
    "そのとき大事にしているポイント(こだわり)は?",
    "{theme}に悩んでいた頃、本当はどうなりたかった?(本音の願い)",
    "読者がキュンとする未来を1シーンで言うと?(例: 子どものお昼寝中にPCを開いて、自分の名前でお仕事してる自分)",
    "それは「何をするだけ」で叶う?",
]

# 訴求タイプごとの定義。
# 「役割」…集客導線の中でどう使う投稿か(出力時の説明にも使う)
# 「書き方」…Claude生成時の指示(PRINCIPLESに上乗せ)
# 「テンプレート」…APIキーなしのときの穴埋め式下書き
APPEALS: dict[str, dict] = {
    "共感": {
        "役割": "売り込みゼロで「わかる!」を集めて信頼をつくる投稿。フォロワー獲得用",
        "書き方": (
            "商品・サービスの宣伝は一切入れない。"
            "1行目のギャップのあと、悩んでいた頃の本音の願いを60点のリアルさで書き、"
            "フォロワーへの問いかけで締めて返信(リプ)を誘う。"
        ),
        "テンプレート": textwrap.dedent("""\
            {hook}
            (悩んでた頃の本音を1〜2行で。例: 本当は「誰か代わって」って毎晩思ってた)
            綺麗にできなくても、今日を乗り切れたらもう十分じゃない?😌
            みんなの本音も聞きたいです。
            #子育てママ #育児あるある"""),
    },
    "お役立ち": {
        "役割": "保存・リポストされやすい実用情報。プロフィールへの流入を増やす投稿",
        "書き方": (
            "教科書的なノウハウではなく「自分がやってるリアルな工夫」を3つ、"
            "番号つきの箇条書きで渡す。それぞれ「〜するだけ」の手軽さを添える。"
            "大事にしているこだわりも1行入れる。"
            "最後に「保存して見返してね」など保存を促す一言を入れる。"
        ),
        "テンプレート": textwrap.dedent("""\
            {hook}
            私が普段やってるリアルな工夫はこれ↓
            ①(工夫1 ※自分のやり方を「〜するだけ」の形で)
            ②(工夫2)
            ③(工夫3)
            こだわりは「(大事にしているポイント)」です。
            どれもするだけ系なのでラクです♡
            保存して見返してね🔖
            #子育てママ #育児ハック"""),
    },
    "体験談": {
        "役割": "ビフォー→アフターで変化を見せ、サービスへの興味を自然に引く投稿",
        "書き方": (
            "ノウハウ説明ではなく変化のストーリーを見せる。"
            "悩んでいた頃の「本音の願い」→「〜するだけ」の小さなきっかけ→"
            "読者がキュンとする未来(BUSINESS_PROFILEのベネフィット)の順。"
            "綺麗にまとめず60点のリアルな自分のまま書く。売り込みは最後の一言まで我慢。"
        ),
        "テンプレート": textwrap.dedent("""\
            {hook}
            ▼あの頃の本音
            (本当はどうなりたかった?を1〜2行で。例: 1人で温かいコーヒーが飲みたかっただけ)
            ▼きっかけ
            ((〜するだけ)の小さな工夫を1行で)
            ▼いま
            {benefit}
            60点の私のままでよかったんだ、って思えてます😌
            #子育てママ"""),
    },
    "お客様の声": {
        "役割": "第三者の声で信頼を裏づける投稿。検討中の人の背中を押す",
        "書き方": (
            "BUSINESS_PROFILEの実績・お客様の声を1つ、会話調で紹介する。"
            "自慢に見えないよう「うれしかった報告」という温度感で書き、"
            "「〜するだけで未来が変わる」手軽さを添えて、最後にさりげなくCTA。"
        ),
        "テンプレート": textwrap.dedent("""\
            {hook}
            うれしい報告をいただきました🥹
            「(お客様の声を1〜2行で)」
            小さな工夫をするだけで、未来はちゃんと変わるんだなぁと実感。
            気になる方は→ {cta}
            #子育てママ"""),
    },
    "告知": {
        "役割": "サービスの案内・行動喚起。共感やお役立ちで信頼を貯めたあとに使う",
        "書き方": (
            "1行目のギャップのあと、ノウハウの説明ではなく"
            "「読者がキュンとする未来」のシーンを具体的に1つ見せる。"
            "「〜するだけ♡」で始められる手軽さを添えて、サービス名とCTAを明記。"
            "誇大表現や過度な限定・煽りは使わない。"
        ),
        "テンプレート": textwrap.dedent("""\
            {hook}
            「(読者がキュンとする未来を1シーンで。例: 子どものお昼寝中に、おうちでお仕事してる自分)」
            それを叶えたくてつくりました。
            {service}
            (〜するだけ)で始められます♡
            ▶ {cta}
            #子育てママ"""),
    },
}


def _profile_text() -> str:
    """BUSINESS_PROFILEをプロンプト用のテキストにする。"""
    lines = [f"- {k}: {v}" for k, v in config.BUSINESS_PROFILE.items()]
    return "\n".join(lines)


def _system_prompt() -> str:
    hooks = "\n".join(
        [f"- {h.format(theme='(テーマ)')}" for h in GAP_HOOK_EXAMPLES]
        + [f"- {h}(お仕事系テーマのとき)" for h in WORK_HOOK_EXAMPLES]
    )
    return textwrap.dedent(f"""\
        あなたは子育て中のママ向けにThreads(スレッズ)を運用し、
        自分のサービスへの集客につなげたいアカウントの中の人です。
        0〜6歳くらいの子どもを育てるママが読者です。

        集客したいサービスの情報:
        {_profile_text()}

        訴求ルール(最優先で守る):
        {PRINCIPLES}

        1行目のギャップの型の例:
        {hooks}

        投稿文のルール:
        - 話し言葉で、友達に話すような自然なトーン。絵文字は1〜3個まで
        - 全体で400文字以内
        - ハッシュタグは2〜4個(#子育てママ など読者が検索しそうなもの)
        - 誇大表現(絶対、必ず○○できる等)や不安を過度に煽る表現は使わない
        - 収入額や成果を保証する表現(「必ず月◯万円稼げる」「誰でも簡単に稼げる」等)は使わない
        - サービス情報が「(例: …)」のままの項目は、無理に使わず「(サービス名)」のように空欄で残す
        """) + generator._buzz_examples()


def _generate_with_claude(theme: str, appeal: str, count: int) -> list[str] | None:
    client = generator._client()
    if client is None:
        return None
    spec = APPEALS[appeal]
    prompt = textwrap.dedent(f"""\
        テーマ「{theme}」で「{appeal}」タイプのThreads投稿文を{count}案書いてください。

        このタイプの役割: {spec["役割"]}
        書き方: {spec["書き方"]}

        必ず1行目は常識と逆の言葉(ギャップ)で始めてください。
        各案は「---」だけの行で区切り、投稿文だけを出力してください(前置き・説明は不要)。
        """)
    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=2048,
            system=_system_prompt(),
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            return None
        text = next((b.text for b in response.content if b.type == "text"), "")
    except Exception:
        return None
    drafts = [d.strip() for d in text.split("\n---") if d.strip()]
    drafts = [d.lstrip("-").strip()[:MAX_LENGTH] for d in drafts]
    return drafts[:count] or None


def _template_draft(theme: str, appeal: str) -> str:
    """APIキーなしでも使える穴埋め式の下書き。"""
    profile = config.BUSINESS_PROFILE
    hook = random.choice(_hook_candidates(theme))
    return APPEALS[appeal]["テンプレート"].format(
        theme=theme,
        hook=hook,
        service=profile.get("サービス名", "(サービス名)"),
        benefit=profile.get("ベネフィット", "(ベネフィット)"),
        cta=profile.get("CTA", "(CTA)"),
    )


def idea_questions(theme: str) -> list[str]:
    """投稿を書く前にノートに書き出す問いかけ(訴求ルール④⑦用)。"""
    return [q.format(theme=theme) for q in IDEA_QUESTIONS]


def make_drafts(theme: str | None, appeal: str | None, count: int) -> list[dict]:
    """下書きを作る。appeal省略時は全タイプ1案ずつ。

    戻り値: [{"theme": ..., "appeal": ..., "text": ...}, ...]
    """
    theme = theme or random.choice(THEMES)
    targets = [(appeal, count)] if appeal else [(a, 1) for a in APPEALS]

    results: list[dict] = []
    for appeal_name, n in targets:
        drafts = _generate_with_claude(theme, appeal_name, n)
        if drafts is None:
            drafts = [_template_draft(theme, appeal_name) for _ in range(n)]
        for text in drafts:
            results.append({"theme": theme, "appeal": appeal_name, "text": text})
    return results


def save_drafts(results: list[dict]) -> str:
    """下書きを data/drafts.md に追記して、ファイルパスを返す。"""
    config.DATA_DIR.mkdir(exist_ok=True)
    path = config.DATA_DIR / "drafts.md"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {now} テーマ: {results[0]['theme']}\n")
        for i, r in enumerate(results, 1):
            f.write(f"\n### 案{i}({r['appeal']})\n\n{r['text']}\n")
    return str(path)
