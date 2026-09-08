# -*- coding: utf-8 -*-
"""下書きを ChatGPT（OpenAI API）で清書する。

    python scripts/polish.py mezame/empath.txt          結果を mezame/empath.polished.txt に保存（元は触らない）
    python scripts/polish.py mezame/empath.txt --apply  検査に通れば元ファイルを置き換える
    python scripts/polish.py mezame/empath.txt --model gpt-4o

APIキーの置き場所（どちらか）:
    ・環境変数 OPENAI_API_KEY
    ・このフォルダ直下の .openai_key ファイル（1行だけ。.gitignore 済み）
  チャットや Git にキーを出さないこと。

検査（1つでも落ちたら置き換えない）:
    ・「 」でくくられた引用文が、前後で完全に一致する
    ・本文中の URL が増えても減ってもいない
    ・見出し（h2/h3）の数が同じ
    ・使わないと決めた語（スピリチュアル、オカルト など）が入っていない
"""
import io
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

BANNED = ["スピリチュアル", "スピ系", "オカルト", "オカルティック", "英語圏", "訳語", "本来は"]

RULES = """あなたは日本語の文章を整える編集者です。以下の下書き（HTML）を、意味・事実・構成を変えずに、
読みやすい自然な日本語に整えてください。

絶対に守ること:
1. 「 」でくくられた引用文は、1文字も変えない。漢字とかなの表記、句読点、送りがなも変えない。
   （例：「もつ」を「持つ」にしない）
2. URL、人名、肩書き、書名、年号、数字は変えない。増やさない。
3. 見出し（<h2>/<h3>）の数と順番は変えない。文言は整えてよい。
4. HTMLのタグ構造（<p> <ul> <li> <div class="fact"> <div class="note"> <table> <a href>）は保つ。
5. 新しい事実や主張を足さない。運営者の意見や助言（「〜するとよいでしょう」）を足さない。
6. 次の語は使わない: スピリチュアル、スピ系、オカルト、オカルティック、英語圏、訳語、本来は、正しくは。
7. 「海外が正しくて日本はずれている」と読める書き方をしない。
8. 読む人の行動を推測する文（「〜な人が多い」「〜だと思います」）を書かない。
9. 効果・治癒・金運・恋愛成就を約束する表現、「絶対」「必ず」「100%」を使わない。
10. 信じている人が読んで、突き放された・笑われたと感じない調子で書く。断定しない。「〜とされる」「〜と述べている」。
11. 太字（<b>）は増やさない。減らすのはよい。

出力は整えたHTML本文だけ。説明や前置きは書かない。"""


def load_key():
    k = os.environ.get("OPENAI_API_KEY", "").strip()
    if k:
        return k
    p = os.path.join(ROOT, ".openai_key")
    if os.path.exists(p):
        return io.open(p, encoding="utf-8").read().strip()
    sys.exit("APIキーが見つかりません。環境変数 OPENAI_API_KEY か、.openai_key ファイルを用意してください。")


def call(model, system, user):
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0.3,
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + load_key()})
    with urllib.request.urlopen(req, timeout=300) as r:
        j = json.loads(r.read().decode("utf-8"))
    return j["choices"][0]["message"]["content"].strip(), j.get("usage", {})


def quotes(t):
    return sorted(re.findall(r"「([^」]*)」", t))


def urls(t):
    return sorted(re.findall(r'href="([^"]+)"', t))


def heads(t):
    return len(re.findall(r"<h[23]>", t))


def check(before, after):
    problems = []
    if quotes(before) != quotes(after):
        a, b = set(quotes(before)), set(quotes(after))
        problems.append("引用が変わっています: 消えた=%s / 増えた=%s" % (sorted(a - b)[:3], sorted(b - a)[:3]))
    if urls(before) != urls(after):
        problems.append("URLが変わっています")
    if heads(before) != heads(after):
        problems.append("見出しの数が違います: %d -> %d" % (heads(before), heads(after)))
    for w in BANNED:
        if w in after and w not in before:
            problems.append("使わない語が入っています: " + w)
    if len(re.findall(r"<b>", after)) > len(re.findall(r"<b>", before)):
        problems.append("太字が増えています")
    if len(after) < len(before) * 0.6:
        problems.append("本文が短くなりすぎています")
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    path = os.path.join(ROOT, args[0])
    apply = "--apply" in sys.argv
    model = "gpt-4o"
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]

    raw = io.open(path, encoding="utf-8").read()
    NL = chr(10)
    sep = NL + "---" + NL
    head, body = raw.split(sep, 1)

    # HTMLのコードフェンスで返ってきたら外す
    out, usage = call(model, RULES, body)
    out = re.sub(r"^```(?:html)?\s*", "", out)
    out = re.sub(r"\s*```$", "", out).strip()

    problems = check(body, out)
    tokens = "%s in / %s out" % (usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?"))
    if problems:
        print("[差し戻し] " + os.path.basename(path) + "  (" + tokens + ")")
        for p in problems:
            print("   - " + p)
        io.open(path.replace(".txt", ".rejected.txt"), "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        sys.exit(1)

    if apply:
        io.open(path, "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        print("[置き換え] " + os.path.basename(path) + "  (" + tokens + ")")
    else:
        p2 = path.replace(".txt", ".polished.txt")
        io.open(p2, "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        print("[保存] " + os.path.basename(p2) + "  (" + tokens + ")  検査は通っています。--apply で置き換え")


if __name__ == "__main__":
    main()
