# -*- coding: utf-8 -*-
"""題名だけ渡して、OpenAI に調べものから記事まで全部やらせる。

    python scripts/ai/research_article.py ascension アセンション
    python scripts/ai/research_article.py ascension アセンション --model gpt-5.6-terra

article.py との違い:
    ・article.py … 既存の記事を材料に、組み直すだけ。ウェブは見ない
    ・これ      … ウェブ検索の道具を使って、自分で調べるところから書く

できるもの:
    mezame/<slug>.gpt.txt          記事の下書き（既存の記事には触りません）
    research/ai/<slug>-gpt/        途中の結果と、出典URLの生死の検査結果

出典URLは、書かれたものが本当に開けるか、1本ずつ確かめます。
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
sys.path.insert(0, HERE)
from article import (BANNED, config, load_key, other_articles, read_article,  # noqa: E402
                     field, inspect)

USAGE = []


def call(step, model, instructions, user, search=False):
    body = {"model": model, "instructions": instructions, "input": user}
    if search:
        body["tools"] = [{"type": "web_search"}]
    for attempt in range(4):
        t0 = time.time()
        req = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + load_key()})
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                j = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            sys.exit("APIエラー(%s) %s: %s" % (e.code, step, msg[:400]))
        u = j.get("usage", {})
        searches = sum(1 for o in j.get("output", []) if o.get("type") == "web_search_call")
        USAGE.append((step, model, u.get("input_tokens", 0), u.get("output_tokens", 0),
                      searches, time.time() - t0))
        out = "".join(c.get("text", "")
                      for o in j.get("output", []) if o.get("type") == "message"
                      for c in o.get("content", []))
        out = re.sub(r"^```(?:html|markdown|json)?\s*", "", out.strip())
        return re.sub(r"\s*```$", "", out).strip()
    sys.exit("APIが応答しません: " + step)


def url_alive(u):
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (mezame link check)"})
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status < 400
    except urllib.error.HTTPError as e:
        return e.code in (403, 405, 406)      # 拒否されただけで、ページはある
    except Exception:
        return False


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    slug, topic = args[0], args[1]
    model = (sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv
             else config("PREMIUM_MODEL", "gpt-5.6-sol"))

    policy = io.open(os.path.join(ROOT, "記事の方針.md"), encoding="utf-8").read()
    rules = io.open(os.path.join(ROOT, "言葉のルール.md"), encoding="utf-8").read()
    related = other_articles(slug)
    cand = NL.join("・%s → %s.html（%s）" % (t, s, d) for s, t, d in related)

    work = os.path.join(ROOT, "research", "ai", slug + "-gpt")
    if not os.path.isdir(work):
        os.makedirs(work)

    def save(n, t):
        io.open(os.path.join(work, n), "w", encoding="utf-8", newline=NL).write(t)

    base = ("あなたは日本語のサイト「めざめ」の書き手です。"
            "次の二つの文書が、このサイトの決まりです。必ず両方に従ってください。"
            + NL + NL + "===== 記事の方針 =====" + NL + policy
            + NL + NL + "===== 言葉のルール =====" + NL + rules)

    sys.stderr.write("「%s」を調べものから書きます（%s）\n" % (topic, model))

    sys.stderr.write("  1/4 リサーチ（ウェブ検索）...\n")
    notes = call("research", model, base + NL + NL +
                 "いまは調べものの段階です。出力は日本語のメモで、記事本文ではありません。",
                 """「%s」について、記事を書くために必要な調べものをしてください。
ウェブ検索の道具を使って、実際にページを見て確かめてください。

調べること:
1. この言葉が、この分野でどう理解されているか。主要な説明のしかた
2. どこから生まれたのか。年号、人名、出来事
3. 読む人が実際に検索している悩みや疑問
4. 日本語では、どう語られているか（英語圏と別に調べること）
5. 関連する概念のうち、本当に関係の深いもの
6. 体や心の不調に関わる部分があれば、安全のために必要な注意

出力の形:
・箇条書きのメモ
・**事実には必ず、確かめたページのURLを添えること**
・最後に「## 出典候補」として、記事に載せられる出典を
  「ラベル | URL | この出典から取った内容」の形で10〜15本

推測で年号や数字を書かないこと。確かめられなかったことは、そう書くこと。""" % topic,
                 search=True)
    save("01_research.md", notes)

    sys.stderr.write("  2/4 構成...\n")
    outline = call("outline", model, base + NL + NL +
                   "いまは構成の段階です。出力は見出し案で、記事本文ではありません。",
                   """「%s」の記事構成を作ってください。

調べものメモ:
%s

同じサイトにある、リンクできる記事:
%s

見出しごとに、そこで何を書くかを1〜2行添えてください。
全体で5,000〜8,000字を想定してください。""" % (topic, notes, cand))
    save("02_outline.md", outline)

    sys.stderr.write("  3/4 本文...\n")
    html_rules = """出力は記事本文のHTMLだけ。前置きや説明を書かない。
使えるタグは <p> <h2> <h3> <ul> <li> <b> <a href="..."> と
<div class="fact">（要点の囲み）<div class="note">（末尾の注意）だけ。
<html> <body> <h1> は書かない。題名と要約は本文に含めない。
内部リンクは <a href="スラッグ.html">…</a> の形。候補にないスラッグへリンクしない。"""
    draft = call("write", model, base + NL + NL + html_rules,
                 """「%s」の本文を書いてください。

構成案:
%s

調べものメモ（ここで確かめた事実だけを使う）:
%s

リンクできる記事（流れに合うものを3〜6本）:
%s

・5,000〜8,000字
・かぎかっこの引用は少なく。引くのは本や事典に載っている言葉だけ
・最後に <div class="note"> で、体の不調があるときは医療にかかることを静かに一言
""" % (topic, outline, notes, cand))
    save("03_draft.html", draft)

    sys.stderr.write("  4/4 編集と仕上げ...\n")
    final = call("edit", model, base + NL + NL + html_rules + NL + NL +
                 """出力は次のJSONだけ。
{"title": "記事の題名", "yomi": "ひらがなの読み", "en": "英語のもとの言い方",
 "tags": "分野を一語で", "summary": "要約120〜200字。読む人の状況から書き始める",
 "related": ["スラッグ", ...],
 "sources": [["ラベル", "URL", "この出典から取った内容"], ...],
 "body": "整えた本文HTML"}""",
                 """次は「%s」の本文です。品質を上げて、上のJSONの形で返してください。

見るところ: 重複、話の飛び、読みにくい長文、同じ語尾の3連続、
使わない語、断定しすぎ、太字の多さ。事実と年号は変えないこと。短くしすぎないこと。

出典は、調べものメモで確かめたもののうち、実際にこの本文の根拠になっているものだけを
10本前後えらび、URLをそのまま写してください。URLを作らないこと。

リンクできる記事: %s

本文:
%s""" % (topic, cand, draft))
    save("04_final.json", final)

    try:
        d = json.loads(re.search(r"\{.*\}", final, re.S).group(0))
    except Exception:
        sys.exit("最後のJSONが読めませんでした: " + os.path.join(work, "04_final.json"))

    # 出典URLが本当に開けるか、1本ずつ確かめる
    sys.stderr.write("\n  出典URLを確かめています...\n")
    good, dead = [], []
    for s in d.get("sources", []):
        if len(s) < 2 or not str(s[1]).startswith("http"):
            continue
        ok = url_alive(s[1])
        (good if ok else dead).append(s)
        sys.stderr.write("    %s %s\n" % ("○" if ok else "×", s[1][:88]))
    save("05_urls.json", json.dumps({"生きている": good, "開けない": dead},
                                    ensure_ascii=False, indent=1))

    # 画像は既存記事のものを引き継ぐ（比べるのは文章なので）
    img = []
    old = os.path.join(ROOT, "mezame", slug + ".txt")
    if os.path.exists(old):
        fm, _, _ = read_article(old)
        img = [l for l in fm if l.startswith(("image:", "image_source:", "image_credit:"))]

    body = d.get("body", "")
    head = ["slug: " + slug,
            "title: " + d.get("title", topic),
            "en: " + d.get("en", ""),
            "yomi: " + d.get("yomi", ""),
            "tags: " + d.get("tags", ""),
            "summary: " + d.get("summary", "").replace(NL, " ")]
    if d.get("related"):
        head.append("related: " + " ".join(d["related"]))
    head += ["source: %s | %s | %s" % (s[0], s[1], s[2] if len(s) > 2 else "") for s in good]
    head += img
    out_path = os.path.join(ROOT, "mezame", slug + ".gpt.txt")
    io.open(out_path, "w", encoding="utf-8", newline=NL).write(
        NL.join(head) + SEP + body + NL)

    # 費用
    price = {"gpt-5.6-sol": (4.0, 20.0), "gpt-5.6-terra": (2.0, 12.0), "gpt-5.6-luna": (0.2, 1.2)}
    sys.stderr.write("\n── かかったもの ──\n")
    ti = to = ns = cost = 0.0
    for step, m, i, o, se, sec in USAGE:
        pi, po = price.get(m, (0, 0))
        c = i / 1e6 * pi + o / 1e6 * po
        sys.stderr.write("  %-9s 入力%7d / 出力%6d  検索%2d回  %5.1f秒  $%.3f\n"
                         % (step, i, o, se, sec, c))
        ti += i
        to += o
        ns += se
        cost += c
    sys.stderr.write("  %-9s 入力%7d / 出力%6d  検索%2d回          $%.3f（検索の料金は別）\n"
                     % ("合計", ti, to, ns, cost))

    problems, n = inspect("", body, d.get("related", []))
    if dead:
        problems.append("開けない出典URLが %d 本あり、外しました" % len(dead))
    sys.stderr.write("\n── できたもの ──\n")
    sys.stderr.write("  %s（本文 %d字／出典 %d本）\n"
                     % (os.path.relpath(out_path, ROOT), n, len(good)))
    if problems:
        sys.stderr.write("\n── 直すところ ──\n")
        for p in problems:
            sys.stderr.write("  ・" + p + NL)
    else:
        sys.stderr.write("\n  検査は通っています。\n")


if __name__ == "__main__":
    main()
