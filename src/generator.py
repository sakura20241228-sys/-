"""投稿文の自動生成。Claude APIがあればAI生成、なければテンプレート生成。"""

from __future__ import annotations

import random
import textwrap

import datetime

from . import analytics, config, trends
from .rakuten import Product

MAX_LENGTH = 480  # Threadsの上限500文字に余裕を持たせる

SYSTEM_PROMPT = """\
あなたは子育て中のママ向けにThreads(スレッズ)を運用しているアカウントの中の人です。
読者は、0〜6歳くらいの子どもを育てるママと、育休中のママ(赤ちゃんと2人きりの日中を過ごしている人)です。

投稿文のルール:
- 話し言葉で、友達に話すような自然なトーン。絵文字は1〜3個まで
- 育児あるあるや実体験風の一言から入ると読まれやすい
- 「私だけじゃないんだ」と思ってもらえる共感・寄り添いの温度感。説教やアドバイス口調にしない
- 最後に軽い問いかけ(「みんなはどうしてる?」など)を入れると返信がつきやすい
- 押し売り感を出さない。「これ良かったよ」という温度感
- 全体で400文字以内
- ハッシュタグは2〜4個(#子育てママ #育休ママ #育児ハック など読者が検索しそうなもの)
- 商品紹介の場合は文末に必ず「#PR」を入れ、リンクは本文にそのまま含める
- 誇大表現(絶対、必ず痩せる等)は使わない
"""


def _client():
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _buzz_examples() -> str:
    """過去にバズった投稿をお手本としてプロンプトに渡す。"""
    tops = analytics.top_posts(3)
    if not tops:
        return ""
    examples = "\n---\n".join(t["text"] for t in tops)
    return f"\n\n過去に反応が良かった投稿(文体・構成の参考にする):\n{examples}"


def _generate_with_claude(prompt: str) -> str | None:
    client = _client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT + _buzz_examples(),
            messages=[{"role": "user", "content": prompt}],
        )
        if response.stop_reason == "refusal":
            return None
        text = next((b.text for b in response.content if b.type == "text"), "")
        return text.strip() or None
    except Exception:
        return None


def affiliate_post(product: Product) -> str:
    """商品紹介投稿を生成する。"""
    prompt = textwrap.dedent(f"""\
        次の楽天の商品を紹介するThreads投稿文を1つ書いてください。
        投稿文だけを出力してください(前置き・説明は不要)。

        商品名: {product.name}
        価格: {product.price}円
        ジャンル: {product.genre_name}
        キャッチコピー: {product.catchcopy}
        レビュー: {product.review_average}点({product.review_count}件)
        リンク(本文に含める): {product.url}
        """)
    text = _generate_with_claude(prompt)
    if text is None:
        text = _template_affiliate(product)
    return _ensure_pr_label(_clip(text, product.url))


def daily_post() -> str:
    """日常(雑談)投稿を生成する。アカウントの信頼感づくり用。

    今日の話題(Googleトレンド/ニュース)が取れればそれを絡め、
    取れなければ内蔵トピック(定番+季節ネタ)から選ぶ。
    """
    topics = trends.trending_topics()
    if topics:
        print(f"今日の話題候補: {' / '.join(topics)}")
        candidates = "\n".join(f"- {t}" for t in topics)
        prompt = textwrap.dedent(f"""\
            今日の話題・トレンドの一覧です:
            {candidates}

            この中から、育休中のママや育児中のママが「わかる〜」と共感したり、
            会話のきっかけにしやすい話題を1つだけ選び、育児の日常と絡めた短い日常投稿を1つ書いてください。
            - 事件・事故・訃報・政治・宗教・炎上系の話題は選ばない
            - ふさわしい話題が1つもなければ、話題は使わず「{random.choice(DAILY_TOPICS)}」をテーマにする
            - 商品紹介やリンクは入れない
            投稿文だけを出力してください(前置き・説明は不要)。
            """)
    else:
        topic = random.choice(DAILY_TOPICS + seasonal_topics())
        prompt = (
            f"「{topic}」をテーマに、育休中のママ・育児中のママの共感を呼ぶ短い日常投稿を1つ書いてください。"
            "商品紹介やリンクは入れないでください。投稿文だけを出力してください。"
        )
    text = _generate_with_claude(prompt)
    if text is None:
        text = random.choice(DAILY_TEMPLATES)
    return _clip(text)


def seasonal_topics() -> list[str]:
    """今の月に合った季節ネタを返す。"""
    return SEASONAL_TOPICS.get(datetime.date.today().month, [])


# ---------- テンプレート(Claude APIなしでも動くように) ----------

DAILY_TOPICS = [
    "寝かしつけあるある",
    "イヤイヤ期の乗り切り方",
    "ワンオペのごはん事情",
    "子どもの寝顔で疲れが吹き飛ぶ瞬間",
    "保育園の準備バタバタ",
    "自分時間の作り方",
    "離乳食の悩み",
    "雨の日の室内遊び",
    # 育休ママ向け
    "育休中、大人と話してない問題",
    "赤ちゃんと2人きりの日中の過ごし方",
    "育休からの職場復帰、正直不安なこと",
    "保活どうしてる?",
    "夫婦の家事育児分担のリアル",
    "産後の自分の体調、後回しにしがち問題",
    "SNSのキラキラ育児と現実のギャップ",
]

SEASONAL_TOPICS = {
    1: ["年末年始明けの生活リズム戻し", "寒い日の公園どうする問題"],
    2: ["花粉と子どもの外遊び", "保育園の合否通知そわそわ"],
    3: ["卒園・進級の準備", "春の入園準備の名前つけ地獄"],
    4: ["慣らし保育で泣く我が子(と自分)", "新生活のバタバタ"],
    5: ["連休明けの登園しぶり", "母の日、自分にもごほうび"],
    6: ["梅雨の室内遊びネタ切れ問題", "雨の日の保育園送迎"],
    7: ["猛暑の公園、何時なら行ける?", "夏の寝かしつけと室温"],
    8: ["お盆の帰省と子連れ移動", "夏休みの昼ごはん無限問題", "汗疹・虫刺されケア"],
    9: ["夏の疲れがどっと出る時期", "運動会の準備"],
    10: ["衣替えでサイズアウト発覚", "ハロウィンの仮装どうする?"],
    11: ["インフルや風邪の季節到来", "年賀状と写真選び"],
    12: ["クリスマスプレゼント隠し場所問題", "年末の大掃除、子どもがいると進まない"],
}

DAILY_TEMPLATES = [
    "寝かしつけ終わってからが自分の時間☕️\nみんなは何して過ごしてる?\n#子育てママ #ワンオペ育児",
    "今日もイヤイヤ期と全力バトルでした🥲\n同じ戦友いたら教えて〜\n#イヤイヤ期 #育児あるある",
    "子どもの寝顔見ると今日の疲れ全部飛ぶのなんでだろう😌\n#子育てママ #育児日記",
    "育休中、気づいたら今日一日大人とまともに話してない…🫠\n同じ人いる?\n#育休ママ #育児あるある",
    "赤ちゃんと2人きりの午後、長いようであっという間🍼\nみんな日中どう過ごしてる?\n#育休中 #子育てママ",
]

AFFILIATE_TEMPLATES = [
    "最近見つけて良かったやつ🥹\n{name}\n{price}円でレビュー{review}点({count}件)はすごい…\n{url}\n#子育てママ #楽天で買ったもの #PR",
    "ママ友に教えてもらってポチったこれ、正解だった✨\n{name}({price}円)\n{url}\n#育児ハック #楽天room #PR",
]


def _template_affiliate(product: Product) -> str:
    template = random.choice(AFFILIATE_TEMPLATES)
    name = product.name[:60] + ("…" if len(product.name) > 60 else "")
    return template.format(
        name=name,
        price=f"{product.price:,}",
        review=product.review_average,
        count=product.review_count,
        url=product.url,
    )


def _ensure_pr_label(text: str) -> str:
    if config.PR_LABEL not in text:
        text = f"{text}\n{config.PR_LABEL}"
    return text


def _clip(text: str, required_url: str = "") -> str:
    """文字数超過を防ぐ。リンクは必ず残す。"""
    if len(text) <= MAX_LENGTH:
        return text
    if required_url and required_url in text:
        body_budget = MAX_LENGTH - len(required_url) - len(config.PR_LABEL) - 4
        body = text.replace(required_url, "").replace(config.PR_LABEL, "").strip()
        return f"{body[:body_budget]}…\n{required_url}\n{config.PR_LABEL}"
    return text[: MAX_LENGTH - 1] + "…"
