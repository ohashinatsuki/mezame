# -*- coding: utf-8 -*-
"""めざめの記事を OpenAI API で書き直す／新しく書く。

    python scripts/ai/article.py rewrite ascension     既存記事を書き直して下書きを作る
    python scripts/ai/article.py rewrite ascension --premium   仕上げに上位モデルを使う

できるもの:
    mezame/<slug>.draft.txt        新しい下書き（元の記事には触りません）
    research/ai/<slug>/            途中の結果（リサーチ・構成・SEO・関連記事）

APIキーの置き場所（どちらか）:
    ・環境変数 OPENAI_API_KEY
    ・このフォルダ直下の .openai_key（1行だけ。.gitignore 済み）
  チャットや Git にキーを出さないこと。

使うモデルは ai.config で変えられます。同じ名前の環境変数があれば、そちらが優先。
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NL = chr(10)
SEP = NL + "---" + NL

BANNED = ["スピリチュアル", "スピ系", "オカルト", "オカルティック", "精神世界",
          "訳語", "本来は", "正しくは", "にすぎない", "思い込み",
          "このサイト", "動画では", "話し手"]

# ── 設定とキー ────────────────────────────────────────────────


def config(name, fallback):
    v = os.environ.get(name, "").strip()
    if v:
        return v
    p = os.path.join(ROOT, "ai.config")
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8"):
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, val = line.split("=", 1)
            if k.strip() == name:
                return val.strip()
    return fallback


def load_key():
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if k:
        return k
    p = os.path.join(ROOT, ".openai_key")
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read().strip()
    sys.exit("APIキーが見つかりません。環境変数 OPENAI_API_KEY か .openai_key を用意してください。")


# ── API 呼び出し ──────────────────────────────────────────────

USAGE = []          # [(段階名, モデル, 入力トークン, 出力トークン, 秒)]


def call(step, model, system, user, temperature=0.4):
    body = {"model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    if temperature is not None:
        body["temperature"] = temperature
    for attempt in range(4):
        t0 = time.time()
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + load_key()})
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                j = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            # temperature を受け付けないモデルなら、外して出し直す
            if "temperature" in msg and "temperature" in body:
                body.pop("temperature")
                continue
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(8 * (attempt + 1))
                continue
            sys.exit("APIエラー(%s) %s: %s" % (e.code, step, msg[:400]))
        u = j.get("usage", {})
        USAGE.append((step, model,
                      u.get("prompt_tokens", 0), u.get("completion_tokens", 0),
                      time.time() - t0))
        out = j["choices"][0]["message"]["content"].strip()
        out = re.sub(r"^```(?:html|markdown|json)?\s*", "", out)
        out = re.sub(r"\s*```$", "", out).strip()
        return out
    sys.exit("APIが応答しません: " + step)


# ── 記事ファイルの読み書き ────────────────────────────────────


def read_article(path):
    raw = io.open(path, encoding="utf-8").read()
    if SEP not in raw:
        sys.exit("本文の区切り --- がありません: " + path)
    head, body = raw.split(SEP, 1)
    fm, sources = [], []
    for line in head.strip().split(NL):
        (sources if line.startswith("source:") else fm).append(line)
    return fm, sources, body.strip()


def field(fm, key):
    for line in fm:
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def other_articles(skip):
    """内部リンクの候補にする、いまある記事の一覧。"""
    out = []
    d = os.path.join(ROOT, "mezame")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".txt") or fn.endswith((".draft.txt", ".gpt.txt",
                                                   ".polished.txt", ".rejected.txt")):
            continue
        slug = fn[:-4]
        if slug == skip:
            continue
        fm, _, _ = read_article(os.path.join(d, fn))
        out.append((slug, field(fm, "title"), field(fm, "summary")[:60]))
    return out


# ── 共通の書き方の指示 ────────────────────────────────────────

VOICE = """あなたは「めざめ」という日本語のサイトの書き手です。
読む人は、この分野に関心がある人、すでにこの考え方に親しんでいる人、
人生の中で不思議な体験や価値観の変化を経験している人です。

## 調子
静かで、神秘的で、温かく、知的で、落ち着いていて、少し文学的。
読む人に寄り添い、押しつけない。子どもっぽくしない。過剰に宗教的にしない。
煽らない。「あなたは選ばれた人です」「これを知らないと危険です」は書かない。
ゆっくり流れる文で書く。短い言い切りの連打をしない。同じ語尾を3回続けない。

## 立ち位置（いちばん大事）
読む人の世界観を否定しない。懐疑を記事の中心にしない。
「科学的に証明されていません」「単なる迷信です」「根拠はありません」を記事の柱にしない。
この分野でその現象がどう理解されているかを、深く、ていねいに説明することが仕事です。
「〜とされています」「〜と理解されています」「〜と結びつけて語られることがあります」を使う。
歴史や来歴（いつ、誰が、どこで言い始めたか）は事実として書いてよい。

## 使わない言葉
スピリチュアル、スピ系、オカルト、精神世界、信じている人、怪しい、トンデモ。
訳語、本来は、正しくは、にすぎない、思い込み。
「このサイトでは」とサイト自身のことを書かない。
「動画では」「話し手は」と出典を指さない。出典は末尾の一覧に置くので、本文は内容を直接述べる。
海外を基準にしない。「英語圏では正しく、日本語ではずれている」と読める書き方をしない。

## 書かないこと
・運営者の意見や助言（「〜するとよいでしょう」「〜が大切です」）
・読む人の行動の推測（「〜な人が多いと思います」）
・効果の約束（治癒・金運・恋愛成就）、「絶対」「必ず」「100%」
・医療の代わりになる断定、危険な行動のすすめ、過度な恐怖

## 安全
体の不調に触れるときは、苦痛が実在するという前提を崩さず、
医療にかかる選択肢を必ず残す。受診を遅らせるような書き方をしない。
違法な薬物を勧めない。"""

HTML_RULES = """出力は記事本文のHTMLだけ。前置きや説明を書かない。
使えるタグは <p> <h2> <h3> <ul> <li> <b> <a href="..."> と
<div class="fact">（要点をまとめた囲み）<div class="note">（末尾の注意）だけ。
<html> <body> <h1> は書かない。題名と要約は別に扱うので本文に含めない。
内部リンクは <a href="スラッグ.html">…</a> の形。指定した候補以外へリンクしない。"""


# ── 各段階 ────────────────────────────────────────────────────


def step_research(model, title, old_body, sources):
    sys.stderr.write("  1/6 リサーチ...\n")
    return call("research", model, VOICE + """

いまは調べものの段階です。出力は日本語のメモ（箇条書き）で、記事本文ではありません。""",
                """次は「%s」という記事の、いまの原稿です。

%s

いま出典として使っているもの:
%s

この原稿を読んで、次の4つを箇条書きで整理してください。

1. この原稿に入っている、残すべき情報（事実、来歴、年号、人名、具体的な説明）
2. 読む人がこの言葉を調べるときに知りたいのに、この原稿に足りていないこと
3. この話題と結びつけて語られる、関連する概念（無理に詰め込まず、本当に関係のあるものだけ）
4. この原稿の作りの問題点（構成、重複、冗長、読みにくさ）

事実を新しく作らないこと。原稿にない年号や統計を足さないこと。
""" % (title, old_body, NL.join(sources)))


def step_outline(model, title, notes, related):
    sys.stderr.write("  2/6 構成...\n")
    cand = NL.join("・%s（%s）" % (t, s) for s, t, _ in related)
    return call("outline", model, VOICE + """

いまは構成を考える段階です。出力は日本語の見出し案（箇条書き）で、記事本文ではありません。""",
                """「%s」という記事の構成を作ってください。

調べものメモ:
%s

同じサイトにある、リンクできる記事:
%s

構成の考え方:
・読む人が実際に感じている疑問や体験から始める
・その言葉が何なのかを、はじめての人にも分かるように説明する
・この分野でどう理解されているかを、いちばん厚く書く
・必要なら、その考えがどこから生まれたのかを書く
・読む人が自分の体験と照らし合わせられる部分を作る
・心理、人生観、人間関係、価値観との関係を掘り下げる
・よくある疑問（FAQ）を入れる
・静かな締めくくりで終える

ただし、この形をそのまま当てはめないこと。この話題に合った構成を考えてください。
見出しごとに、そこで何を書くかを1〜2行で添えてください。
全体で5,000〜8,000字になる分量を想定してください。
""" % (title, notes, cand))


def step_write(model, title, outline, notes, old_body, related):
    sys.stderr.write("  3/6 本文...\n")
    cand = NL.join("・%s → %s.html" % (t, s) for s, t, _ in related)
    return call("write", model, VOICE + NL + NL + HTML_RULES,
                """「%s」という記事の本文を書いてください。

構成案:
%s

調べものメモ:
%s

いまの原稿（事実の出どころ。ここにある事実だけを使ってください）:
%s

リンクできる記事（この中から、本文の流れに合うものだけを2〜5本）:
%s

大事なこと:
・いまの原稿にある事実、年号、人名、来歴は正確に引き継ぐ。新しい事実を作らない
・いまの原稿は引用の継ぎはぎになっています。引用符でつなぐのをやめ、
  自分の言葉で説明する文章にしてください。かぎかっこで引くのは、
  本や事典に載っている言葉だけにし、数は少なくすること
・5,000〜8,000字。字数を埋めるための冗長な文を書かない
・最後に <div class="note"> で、体の不調があるときは医療にかかることを、静かに一言
""" % (title, outline, notes, old_body, cand))


def step_edit(model, title, draft):
    sys.stderr.write("  4/6 編集...\n")
    return call("edit", model, VOICE + NL + NL + HTML_RULES,
                """次は「%s」の本文です。品質を上げて、整えたHTMLだけを返してください。

見るところ:
・同じことを二度書いていないか。重複を整理する
・話の順番に飛びがないか
・読みにくい長い文、硬い言い回しを直す
・同じ語尾が3回続いていないか
・使わない言葉が入っていないか
・断定しすぎていないか
・太字が多すぎないか（囲みの見出しと、各節の要点だけ）

事実、年号、人名、リンク先、見出しの数は変えないこと。
短くしすぎないこと。

%s""" % (title, draft))


def step_seo(model, title, draft):
    sys.stderr.write("  5/6 SEO...\n")
    out = call("seo", model, "あなたは日本語のSEO編集者です。出力はJSONだけ。",
               """次の記事に、検索から来る人に向けた情報を作ってください。

JSONで、次の3つだけを返してください。
{"title": "検索結果に出す題名（30字以内、煽らない）",
 "summary": "記事の要約（120〜200字。読む人の状況から書き始める。この分野の言葉を使ってよい）",
 "yomi": "題名のひらがな読み"}

記事の題名: %s
本文:
%s""" % (title, draft[:6000]), temperature=0.2)
    try:
        return json.loads(re.search(r"\{.*\}", out, re.S).group(0))
    except Exception:
        return {}


def step_related(model, title, draft, related):
    sys.stderr.write("  6/6 関連記事...\n")
    cand = NL.join("%s | %s | %s" % (s, t, d) for s, t, d in related)
    out = call("related", model, "あなたは日本語の編集者です。出力はJSONだけ。",
               """「%s」の記事から、読む人が次に読みたくなる記事を4〜6本えらんでください。

候補（スラッグ | 題名 | 説明）:
%s

本文の抜粋:
%s

JSONで {"related": ["スラッグ", "スラッグ", ...]} だけを返してください。
候補にないスラッグを書かないこと。関係の薄いものを無理に入れないこと。
""" % (title, cand, draft[:4000]), temperature=0.2)
    try:
        return json.loads(re.search(r"\{.*\}", out, re.S).group(0)).get("related", [])
    except Exception:
        return []


# ── 検査 ──────────────────────────────────────────────────────


def inspect(old_body, new_body, related_slugs):
    p = []
    for t in ("div", "p", "ul", "li", "b", "h2", "h3", "a"):
        o = len(re.findall(r"<%s[ >]" % t, new_body))
        c = new_body.count("</%s>" % t)
        if o != c:
            p.append("タグが閉じていません: <%s> %d 個に対して </%s> %d 個" % (t, o, t, c))
    for w in BANNED:
        if w in new_body:
            p.append("使わない語が入っています: " + w)
    for h in re.findall(r'href="([^"#:]+\.html)"', new_body):
        if not os.path.exists(os.path.join(ROOT, h)):
            p.append("リンク先がありません: " + h)
    n = len(re.sub(r"<[^>]+>", "", new_body))
    if n < 3500:
        p.append("本文が短すぎます: %d字" % n)
    if n > 12000:
        p.append("本文が長すぎます: %d字" % n)
    if new_body.count("「") > 25:
        p.append("かぎかっこの引用が多すぎます: %d個" % new_body.count("「"))
    if "<h1" in new_body or "<html" in new_body:
        p.append("<h1> か <html> が入っています")
    return p, n


def report_cost():
    sys.stderr.write("\n── かかったもの ──\n")
    ti = to = 0
    for step, model, i, o, sec in USAGE:
        sys.stderr.write("  %-9s %-14s 入力%7d / 出力%6d トークン  %5.1f秒\n" % (step, model, i, o, sec))
        ti += i
        to += o
    sys.stderr.write("  %-24s 入力%7d / 出力%6d トークン\n" % ("合計", ti, to))
    io.open(os.path.join(ROOT, "research", "ai", "last_usage.json"), "w", encoding="utf-8").write(
        json.dumps([{"step": s, "model": m, "in": i, "out": o, "sec": round(t, 1)}
                    for s, m, i, o, t in USAGE], ensure_ascii=False, indent=1))


# ── 本体 ──────────────────────────────────────────────────────


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2 or args[0] != "rewrite":
        sys.exit(__doc__)
    slug = args[1]
    path = os.path.join(ROOT, "mezame", slug + ".txt")
    if not os.path.exists(path):
        sys.exit("記事が見つかりません: " + path)

    article_model = config("ARTICLE_MODEL", "gpt-5.6-luna")
    editor_model = config("PREMIUM_MODEL" if "--premium" in sys.argv else "EDITOR_MODEL",
                          "gpt-5.6-terra")

    fm, sources, old_body = read_article(path)
    title = field(fm, "title")
    related = other_articles(slug)
    work = os.path.join(ROOT, "research", "ai", slug)
    if not os.path.isdir(work):
        os.makedirs(work)

    def save(name, text):
        io.open(os.path.join(work, name), "w", encoding="utf-8", newline=NL).write(text)

    sys.stderr.write("「%s」を書き直します（%s ／ 仕上げ %s）\n" % (title, article_model, editor_model))

    notes = step_research(article_model, title, old_body, sources)
    save("01_research.md", notes)
    outline = step_outline(editor_model, title, notes, related)
    save("02_outline.md", outline)
    draft = step_write(article_model, title, outline, notes, old_body, related)
    save("03_draft.html", draft)
    draft = step_edit(editor_model, title, draft)
    save("04_edited.html", draft)
    seo = step_seo(article_model, title, draft)
    save("05_seo.json", json.dumps(seo, ensure_ascii=False, indent=1))
    rel = step_related(article_model, title, draft, related)
    save("06_related.json", json.dumps(rel, ensure_ascii=False, indent=1))

    # 前書きは元の記事から引き継ぐ。出典・画像・スラッグは触らない。
    new_fm = []
    for line in fm:
        if line.startswith("summary:") and seo.get("summary"):
            line = "summary: " + seo["summary"].replace(NL, " ")
        new_fm.append(line)
    if rel:
        new_fm.append("related: " + " ".join(rel))
    out = NL.join(new_fm) + NL + NL.join(sources) + SEP + draft + NL

    draft_path = os.path.join(ROOT, "mezame", slug + ".draft.txt")
    io.open(draft_path, "w", encoding="utf-8", newline=NL).write(out)

    problems, n = inspect(old_body, draft, rel)
    report_cost()
    sys.stderr.write("\n── できたもの ──\n")
    sys.stderr.write("  %s（本文 %d字／もとは %d字）\n"
                     % (os.path.relpath(draft_path, ROOT), n,
                        len(re.sub(r"<[^>]+>", "", old_body))))
    sys.stderr.write("  途中の結果: %s\n" % os.path.relpath(work, ROOT))
    if problems:
        sys.stderr.write("\n── 直すところ ──\n")
        for p in problems:
            sys.stderr.write("  ・" + p + "\n")
    else:
        sys.stderr.write("\n  検査は通っています。\n")


if __name__ == "__main__":
    main()
