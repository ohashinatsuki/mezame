# -*- coding: utf-8 -*-
"""固定ページ（このサイトについて等）の文章を Terra に書き直させる。

    python scripts/polish_page.py about.html            結果を about.polished.html に保存（元は触らない）
    python scripts/polish_page.py about.html --apply    検査に通れば元を置き換える

記事（mezame/*.txt）用の polish.py と違い、こちらは HTML ページの <main> の中だけを書き直す。
法律にかかわる節（運営者・訂正について・免責・プライバシー）は、意味が変わると困るので触らせない。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polish  # call / BANNED / default_model を使い回す

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NL = chr(10)

# ここから下は書き直さない（法律・事実にかかわる部分）
FREEZE_FROM = re.compile(r"<h2>\s*運営者\s*</h2>")

RULES = """あなたは日本語のウェブサイトの書き手です。以下はサイトの固定ページの本文（HTML）です。
同じことを伝えたまま、あなた自身の言葉で書き直してください。文をなぞる必要はありません。

このサイトは、ツインレイ・エンパス・月星座など、この分野の言葉を、誰がどう言っているかという形で
出典つきに書いている資料サイトです。何も売っていません。名前は「めざめのノート」です。

自由にしてよいこと:
- 言い回し、段落の切り方、文の順番を変える
- 見出しの文言を変える（数と順番は変えない）
- 箇条書きの言い方を変える

守ること:
1. HTMLの部品（<h1> <h2> <h3> <p> <ul> <li> <b> <a href> <div class="note"> <div class="fact"> class属性）はそのまま使う。
   見出し（<h1>/<h2>/<h3>）の数と順番は変えない。リンク（<a href>）は増やさない・減らさない・宛先を変えない。
2. 新しい約束や事実を足さない。書かれていないことを書かない。
3. 「受診をためらわないでください」という趣旨は必ず残す。医療の情報ではないという断りも残す。
4. 会員登録・メールアドレス・生年月日についての説明は、意味を変えない（どこにも送られない、という点）。
5. 次の語は使わない: スピリチュアル、スピ系、オカルト、オカルティック、英語圏、訳語、本来は、正しくは。
6. 読む人を分類しない（「信じている人」「〜に興味のある方へ」と呼びかけない）。
7. 読む人の行動を推測しない（「〜な人が多い」「〜だと思います」）。
8. 効果・治癒・金運・恋愛成就を約束しない。「絶対」「必ず」「100%」を使わない。
9. サイトが自分のやり方を誇らない（「何も売りません」「登録もいりません」を売り文句にしない）。
10. 調子は静かで、落ち着いていて、温かい。煽らない。同じ語尾を3回続けない。
11. 分量は元と同じくらい。

出力は書き直したHTML本文だけ。説明や前置きは書かない。"""


def heads(t):
    return re.findall(r"<h([123])>", t)


def links(t):
    return sorted(re.findall(r'href="([^"]+)"', t))


def check(before, after):
    bad = []
    if heads(before) != heads(after):
        bad.append("見出しの数か順番が違います: %s -> %s" % (heads(before), heads(after)))
    if links(before) != links(after):
        bad.append("リンクが変わっています")
    for w in polish.BANNED:
        if w in after and w not in before:
            bad.append("使わない語が入っています: " + w)
    if "受診" not in after:
        bad.append("受診についての一文が消えています")
    if len(after) < len(before) * 0.7 or len(after) > len(before) * 1.5:
        bad.append("分量が離れすぎています: %d -> %d" % (len(before), len(after)))
    return bad


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    path = os.path.join(ROOT, args[0])
    apply = "--apply" in sys.argv
    model = polish.default_model()

    s = io.open(path, encoding="utf-8").read()
    m = re.search(r"<main.*?</main>", s, re.S)
    if not m:
        sys.exit("<main> が見つかりません: " + path)
    main_html = m.group(0)

    # 法律にかかわる節から後ろは凍結
    fz = FREEZE_FROM.search(main_html)
    target, frozen = (main_html[:fz.start()], main_html[fz.start():]) if fz else (main_html, "")

    user = target
    for attempt in (1, 2, 3):
        out, usage = polish.call(model, RULES, user)
        out = re.sub(r"^```(?:html)?\s*", "", out)
        out = re.sub(r"\s*```$", "", out).strip()
        bad = check(target, out)
        if not bad:
            break
        if attempt < 3:
            print("[やり直し] %d回目: %s" % (attempt, " / ".join(bad)))
            user = target + NL + NL + "【前回の問題】" + NL + NL.join("- " + b for b in bad)
    if bad:
        print("[差し戻し] " + os.path.basename(path))
        for b in bad:
            print("   - " + b)
        sys.exit(1)

    new_page = s[:m.start()] + out + frozen + s[m.end():]
    tokens = "%s in / %s out" % (usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?"))
    if apply:
        io.open(path, "w", encoding="utf-8", newline=NL).write(new_page)
        print("[置き換え] " + os.path.basename(path) + "  (" + tokens + ")")
    else:
        p2 = path.replace(".html", ".polished.html")
        io.open(p2, "w", encoding="utf-8", newline=NL).write(new_page)
        print("[保存] " + os.path.basename(p2) + "  (" + tokens + ")")


main()
