"""集客用のThreads投稿文づくりを手伝うツール。

育児ママ向けに自分のサービス・商品へ集客したいアカウントのための
下書きジェネレーター。

  python main.py copy                       # 全訴求タイプ1案ずつ
  python main.py copy --theme 寝かしつけ     # テーマ指定
  python main.py copy --appeal 共感 --count 3  # 訴求タイプ指定で3案

Claude APIキーがあれば完成形の投稿文を、なければ穴埋め式の
構成テンプレート(そのまま埋めれば投稿できる形)を出力する。

訴求の方向性が決まったら:
- src/config.py の BUSINESS_PROFILE にサービス情報を記入
- このファイルの APPEALS の「書き方」を好みに合わせて調整
"""

from __future__ import annotations

import datetime
import random
import textwrap

from . import analytics, config, generator

MAX_LENGTH = 480  # Threadsの上限500文字に余裕を持たせる

# 集客アカウントで反応を取りやすい育児テーマ(--theme 省略時にここから選ぶ)
THEMES = [
    "寝かしつけ",
    "イヤイヤ期",
    "離乳食・好き嫌い",
    "ワンオペ育児",
    "夜泣き",
    "トイトレ",
    "自分時間がない",
    "保育園・幼稚園の準備",
    "子どもの習い事選び",
    "産後の体力・メンタル",
]

# 訴求タイプごとの定義。
# 「役割」…集客導線の中でどう使う投稿か(出力時の説明にも使う)
# 「書き方」…Claude生成時の指示
# 「テンプレート」…APIキーなしのときの穴埋め式下書き
APPEALS: dict[str, dict] = {
    "共感": {
        "役割": "売り込みゼロで「わかる!」を集めて信頼をつくる投稿。フォロワー獲得用",
        "書き方": (
            "商品・サービスの宣伝は一切入れない。"
            "テーマの大変さに共感する実体験風のエピソードを1〜2行入れ、"
            "フォロワーへの問いかけで締めて返信(リプ)を誘う。"
        ),
        "テンプレート": textwrap.dedent("""\
            {theme}、今日もなかなかの強敵でした…🥲
            (具体的なエピソードを1〜2行で)
            同じ悩みのママさん、どう乗り切ってますか?
            #子育てママ #育児あるある"""),
    },
    "お役立ち": {
        "役割": "保存・リポストされやすい実用情報。プロフィールへの流入を増やす投稿",
        "書き方": (
            "テーマに関する具体的で今日から試せるコツを3つ、番号つきの箇条書きで。"
            "最後に「保存して見返してね」など保存を促す一言を入れる。"
            "サービスの宣伝は入れないか、入れても最後に一言だけ。"
        ),
        "テンプレート": textwrap.dedent("""\
            【{theme}がちょっとラクになる3つのコツ】
            ①(コツ1)
            ②(コツ2)
            ③(コツ3)
            いろいろ試した中でこれが1番効きました✨
            保存して見返してね🔖
            #子育てママ #育児ハック"""),
    },
    "体験談": {
        "役割": "ビフォー→アフターで変化を見せ、サービスへの興味を自然に引く投稿",
        "書き方": (
            "「昔の自分」がテーマにどれだけ悩んでいたか(ビフォー)→"
            "変わったきっかけ→今どうなったか(アフター)の順で書く。"
            "アフターにはBUSINESS_PROFILEのベネフィットを自然に織り込む。"
            "売り込みは最後の一言まで我慢する。"
        ),
        "テンプレート": textwrap.dedent("""\
            {theme}に悩んでた頃の私に教えてあげたい。
            ▼before
            (どれだけ大変だったかを1〜2行で)
            ▼きっかけ
            (変わったきっかけを1行で)
            ▼after
            {benefit}
            同じ悩みのママの参考になったらうれしいです😌
            #子育てママ"""),
    },
    "お客様の声": {
        "役割": "第三者の声で信頼を裏づける投稿。検討中の人の背中を押す",
        "書き方": (
            "BUSINESS_PROFILEの実績・お客様の声を1つ、会話調で紹介する。"
            "自慢に見えないよう「うれしかった報告」という温度感で書き、"
            "最後にさりげなくCTAを添える。"
        ),
        "テンプレート": textwrap.dedent("""\
            うれしい報告をいただきました🥹
            「(お客様の声を1〜2行で)」
            {theme}に悩むママの力になれるのが本当にうれしい…!
            気になる方は→ {cta}
            #子育てママ"""),
    },
    "告知": {
        "役割": "サービスの案内・行動喚起。共感やお役立ちで信頼を貯めたあとに使う",
        "書き方": (
            "テーマに悩む読者に向けて、サービス名・ベネフィット・CTAを明記した告知文。"
            "「〜な方へ」と対象を絞る一文から入る。"
            "誇大表現や過度な限定・煽りは使わない。"
        ),
        "テンプレート": textwrap.dedent("""\
            【お知らせ】
            {theme}に悩んでいるママへ。
            {service}
            {benefit}
            ▶ {cta}
            #子育てママ"""),
    },
}


def _profile_text() -> str:
    """BUSINESS_PROFILEをプロンプト用のテキストにする。"""
    lines = [f"- {k}: {v}" for k, v in config.BUSINESS_PROFILE.items()]
    return "\n".join(lines)


def _system_prompt() -> str:
    return textwrap.dedent(f"""\
        あなたは子育て中のママ向けにThreads(スレッズ)を運用し、
        自分のサービスへの集客につなげたいアカウントの中の人です。
        0〜6歳くらいの子どもを育てるママが読者です。

        集客したいサービスの情報:
        {_profile_text()}

        投稿文のルール:
        - 話し言葉で、友達に話すような自然なトーン。絵文字は1〜3個まで
        - 全体で400文字以内
        - ハッシュタグは2〜4個(#子育てママ など読者が検索しそうなもの)
        - 誇大表現(絶対、必ず○○できる等)や不安を過度に煽る表現は使わない
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
    return APPEALS[appeal]["テンプレート"].format(
        theme=theme,
        service=profile.get("サービス名", "(サービス名)"),
        benefit=profile.get("ベネフィット", "(ベネフィット)"),
        cta=profile.get("CTA", "(CTA)"),
    )


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
