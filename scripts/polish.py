# -*- coding: utf-8 -*-
"""下書きを ChatGPT（OpenAI API）で清書する。

    python scripts/polish.py mezame/empath.txt          結果を mezame/empath.polished.txt に保存（元は触らない）
    python scripts/polish.py mezame/empath.txt --apply  検査に通れば元ファイルを置き換える
    python scripts/polish.py mezame/empath.txt --model gpt-5.6-sol   （既定は ai.config の EDITOR_MODEL）
    python scripts/polish.py mezame/empath.txt --strict             なめらかにするだけ（既定は自由モード。自分の言葉で書き直す）
    python scripts/polish.py mezame/empath.txt --tag sol            結果を mezame/empath.sol.txt に保存
    python scripts/polish.py mezame/empath.txt --summary-only       本文は触らず、要約（リード文）だけ本文に合わせて作り直す

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

そのうえで、読まれる文章にすること:
12. 冒頭の1〜2文は、読む人が抱えている状況をその人の言葉で言い当てる形にして、先を読みたくなるようにする。
    ただし煽らない（「あなたは選ばれた」「知らないと危険」「今すぐ」の型は使わない）。
13. 見出し（<h2>/<h3>）は、記事の主題の言葉（例：ツインレイ、エンパス）と、読む人が検索窓に打つ
    悩みの言葉（例：離れてしまった、消耗する）を自然に含めた、具体的で短いものにする。
    抽象的な見出し（「はじめに」「まとめ」「考察」）は具体的な内容に言い換える。
14. 記事の主題の言葉は、冒頭の段落と各見出しに自然に入れる。同じ語を不自然に何度も繰り返さない。
15. 段落の最初の1文にその段落の要点を置く。長い文は2つに分けてよい。
    ただし短い言い切りの連打にはしない。「〜ことがあります」「〜と述べています」のようにゆっくり流す調子は保つ。
16. 調子は、静か・温かい・落ち着いている・少し文学的。子どもっぽくしない。煽り記事にしない。

出力は整えたHTML本文だけ。説明や前置きは書かない。"""


FREE_RULES = """あなたは日本語のウェブ記事の書き手です。以下の下書き（HTML）は素材です。同じ主題・同じ事実・同じ出典を使って、
あなた自身の記事を書いてください。下書きの文も段落も構成も、なぞる必要はまったくありません。
別の書き手が同じ材料で一から書いた記事、という気持ちで書いてください。

自由にしてよいこと:
- 構成を組み替える。話す順番を変える。悩みから入っても、場面から入っても、問いから入ってもよい
- 段落を増やす、減らす、分ける、つなぐ。見出しを立て直す、増やす、減らす
- 言い回しを全部変える。比喩、情景、語りかけ、間（ま）を使う。文の長短をつけてリズムを作る
- 下書きが説明を省いているところを、素材の範囲内でていねいに言葉にする
- 下書きの冗長なところ、繰り返しを削る
- 分量は下書きより多くても少なくてもよい（目安は7割〜1.5倍）

絶対に守ること:
1. 「 」でくくられた引用文（人の言葉・資料の言葉）は、1文字も変えない。漢字とかなの表記、句読点、送りがなも変えない。
   どの引用文も必ず本文のどこかに残す。文を組み替えるときも、引用文だけは丸ごと持っていくこと。
   引用文以外の語句を新しく「 」でくくらない（用語の強調に「 」を使わない）。
2. URL、人名、肩書き、書名、年号、数字は変えない。増やさない。減らさない。
   リンク（<a href>）は元にあるものをそのまま使う。新しいリンクを足さない。参考資料の出典をリンクにしない。
3. 新しい事実や主張を足さない。運営者の意見や助言（「〜するとよいでしょう」）を足さない。
4. HTMLの部品（<p> <h2> <h3> <ul> <li> <div class="fact"> <div class="note"> <table> <a href>）だけで書く。
   <div class="fact"> と <div class="note"> の中身はその役割のまま残す。
5. 次の語は地の文で使わない: スピリチュアル、スピ系、オカルト、オカルティック、英語圏、訳語、本来は、正しくは。
   ただし「 」の引用文の中にこれらの語がある場合は、引用なのでそのまま残す（引用ごと落とさない）。
6. 「海外が正しくて日本はずれている」と読める書き方をしない。
7. 読む人の行動を推測する文（「〜な人が多い」「〜だと思います」）を書かない。
8. 効果・治癒・金運・恋愛成就を約束する表現、「絶対」「必ず」「100%」を使わない。
9. 信じている人が読んで、突き放された・笑われたと感じない調子で書く。断定しない。「〜とされる」「〜と述べている」。
10. 太字（<b>）は増やさない。
11. 水増ししない。言葉を増やすなら、読む人の理解が深まるところにだけ。

読まれる記事にすること:
12. 冒頭の1〜2文は、読む人が抱えている状況をその人の言葉で言い当てる形にして、先を読みたくなるようにする。
    短い文で始めてよい。ただし煽らない（「あなたは選ばれた」「知らないと危険」「今すぐ」の型は使わない）。
13. 見出しは、記事の主題の言葉と、読む人が検索窓に打つ悩みの言葉を自然に含めた、具体的で短いものにする。
    主題の言葉を全部の見出しに入れる必要はなく、半分くらいでよい。
    記事の型（悩み → 誰がどう言っているか → 何をすればよいと言われているか → 来歴・整理）は保つが、その中は自由。
14. 記事の主題の言葉は冒頭の段落に自然に入れる。同じ語を不自然に何度も繰り返さない。
15. 段落の最初の1文にその段落の要点を置く。
16. 調子は、静か・温かい・落ち着いている・少し文学的。ゆっくり流れる語り口。子どもっぽくしない。煽り記事にしない。
    ただし同じ語尾を3回続けない。

これは誰か一人の語りではなく、一般論として書く記事です。次の書き方をしない:
17. 読む人に「あなた」と呼びかけない。「読んでいるあなたも」「あなたが選んだ」のような書き方をしない。
    主語を置かずに書くか、「読む人」「その人」と 三人称で書く。
18. 読む人に指図しない。「〜してください」「〜しましょう」「〜してほしい」「気をつけてほしいのは」を使わない。
    「〜と言われています」「〜という注意が添えられています」の形にする。
19. 「私たち」と書かない。動画やインタビューの語り手の一人称を、そのまま地の文に持ち込まない。
20. 運営者が重みづけしない。「このページでいちばん大事なこと」「〜と思います」「〜ではないでしょうか」を使わない。

**例外**: 体や命にかかわる案内（受診、検査、相談窓口、緊急時）は、これまでどおり
「医療機関に相談してください」の形のまま残すこと。ここだけは呼びかけてよい。

出力は書き直したHTML本文だけ。説明や前置きは書かない。"""


SUMMARY_RULES = """あなたは日本語のウェブ記事の編集者です。以下の記事本文（HTML）を読み、ページの冒頭に置くリード文を1つ書いてください。
検索結果の説明文（メタディスクリプション）にもそのまま使います。

条件:
- 120〜200文字。1段落。改行しない。HTMLタグを使わない
- 最初の1文は、読む人が抱えている状況をその人の言葉で短く言い当てる（例:「時計を見るたびに11:11。」）
- 記事の主題の言葉を前半に自然に入れる（検索で拾われるように）。ただし詰め込まない
- この記事で何が分かるかを、誰の言葉を引いているかも含めて具体的に
- 煽らない。「あなたは選ばれた」「知らないと危険」「今すぐ」の型は使わない
- 次の語は使わない: スピリチュアル、スピ系、オカルト、オカルティック、英語圏、訳語、本来は、正しくは
- 読む人の行動を推測しない（「〜な人が多い」「〜だと思います」）。運営者の意見や助言を書かない
- 効果・治癒・金運・恋愛成就を約束しない。「絶対」「必ず」「100%」を使わない

出力はリード文だけ。前置きも説明も書かない。"""


def write_summary(model, body):
    """新しい本文に合わせた要約（リード文）を書かせる。条件に合わなければ None。"""
    out, usage = call(model, SUMMARY_RULES, body)
    out = re.sub(r"\s+", " ", out).strip().strip("「」\"'")
    # 対になっていないかっこを消す（「…。」で始めて外側だけ削れた場合など）
    depth, cleaned = 0, []
    for ch in out:
        if ch == "「":
            depth += 1
        elif ch == "」":
            if depth == 0:
                continue
            depth -= 1
        cleaned.append(ch)
    out = "".join(cleaned).replace("「", "「") if depth == 0 else "".join(cleaned).replace("「", "")
    if not (80 <= len(out) <= 260) or "<" in out or any(w in out for w in BANNED):
        return None, usage
    return out, usage


def replace_summary(head, summary):
    lines = head.split(chr(10))
    for i, l in enumerate(lines):
        if l.startswith("summary:"):
            lines[i] = "summary: " + summary
            break
    return chr(10).join(lines)


def default_model():
    """ai.config の POLISH_MODEL（書き直し用）を既定にする。無ければ EDITOR_MODEL、それも無ければ gpt-5.6-terra。"""
    p = os.path.join(ROOT, "ai.config")
    conf = {}
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8"):
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip()
    return conf.get("POLISH_MODEL") or conf.get("EDITOR_MODEL") or "gpt-5.6-terra"


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
            # temperature は指定しない（gpt-5.6 系は既定値以外を受け付けない）
        }).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + load_key()})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            j = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("APIがエラーを返しました (HTTP %d):\n%s" % (e.code, e.read().decode("utf-8", "replace")[:800]))
    return j["choices"][0]["message"]["content"].strip(), j.get("usage", {})


def quotes(t):
    # 引用文の中の太字などのタグは無視して比べる
    return sorted(re.findall(r"「([^」]*)」", re.sub(r"<[^>]+>", "", t)))


def urls(t):
    return sorted(re.findall(r'href="([^"]+)"', t))


CITE_MARK = re.compile(u"^[^「」]{0,15}?(と述べ|と書い|と書か|と語|と記し|と記さ|とある|と説明|と紹介|と話し|と答え|と呼びかけ|と警告|と言っ|と言い|と言わ|とされ|と伝え|と続け|と表現|と定義|と締め|と結ん)")


def citations(t):
    """「 」のうち、人や資料の言葉とみなすもの。
    ・20文字以上のもの
    ・8文字以上で、閉じかっこの直後に「と述べている」「とある」などの引用の目印が続くもの
    用語や言い回しを「 」でくくっただけのものは含めない。"""
    out = set()
    t = re.sub(r"<[^>]+>", "", t)
    for m in re.finditer(r"「([^」]*)」", t):
        q = m.group(1)
        if len(q) >= 20:
            out.add(q)
        elif len(q) >= 8 and CITE_MARK.search(t[m.end():m.end() + 25]):
            out.add(q)
    return out


# 体・命にかかわる案内は、読む人に呼びかけてよい（残す）
SAFE_NEAR = re.compile("医療|受診|診てもら|病院|医師|主治医|検査|心電図|眼科|睡眠外来|精神科|"
                       "いのちの電話|ホットライン|相談ナビ|警察|救急|自殺|傷つける|緊急")

# 誰かが話しているように読める書き方（一般論として書く記事には合わない）
VOICE = [("読む人への呼びかけ「あなた」", "あなた"),
         ("運営者の助言（〜てください／ましょう／ほしい）", "てください|てほしい|ていただきたい|ましょう"),
         ("語り手の「私たち」", "私たち|わたしたち|私の経験|私のクライアント"),
         ("運営者の感想", "と思います|のではないでしょうか"),
         ("運営者が重みづけする言い方", "(?:いちばん|一番|最も)(?:大事|大切|重要)")]


def voice_problems(t):
    """引用「」の外で、誰かが話しているように読める箇所を拾う。
    体・命にかかわる案内（前後60字以内に医療の語がある）は見逃す。"""
    plain = re.sub(r"「[^」]*」", "＿", re.sub(r"<[^>]+>", "", t))
    out = []
    for name, pat in VOICE:
        for m in re.finditer(pat, plain):
            around = plain[max(0, m.start() - 60):m.start() + 60]
            if SAFE_NEAR.search(around):
                continue
            out.append("%s: …%s…" % (name, plain[max(0, m.start() - 25):m.start() + 25].replace(chr(10), " ")))
    return out


def heads(t):
    return len(re.findall(r"<h[23]>", t))


def check(before, after, free=False):
    problems = []
    if free:
        # 自由モード: 用語を「 」でくくる程度の増減は許す。
        #   落とすのは (a) 8文字以上の引用（＝人の言葉）が消えた  (b) 元の本文に無い文を「 」で作った  の2つ
        qb, qa = set(quotes(before)), set(quotes(after))
        plain_before = re.sub(r"<[^>]+>", "", before)
        lost = sorted(q for q in citations(before) if q not in qa)
        made = sorted(q for q in qa - qb if q not in plain_before)
        if lost:
            problems.append("引用が消えています: %s" % lost[:3])
        if made:
            problems.append("元に無い引用が作られています: %s" % made[:3])
        for v in voice_problems(after)[:3]:
            problems.append("誰かが話しているように読めます — " + v)
        ub, ua = set(urls(before)), set(urls(after))
        if ub - ua:
            problems.append("リンクが消えています: %s" % sorted(ub - ua)[:3])
        if ua - ub:
            problems.append("リンクが増えています: %s" % sorted(ua - ub)[:3])
    else:
        if quotes(before) != quotes(after):
            a, b = set(quotes(before)), set(quotes(after))
            problems.append("引用が変わっています: 消えた=%s / 増えた=%s" % (sorted(a - b)[:3], sorted(b - a)[:3]))
        if urls(before) != urls(after):
            problems.append("URLが変わっています")
    if free:
        if heads(after) < 2 or heads(after) > heads(before) + 5:
            problems.append("見出しの数が極端です: %d -> %d" % (heads(before), heads(after)))
    elif heads(before) != heads(after):
        problems.append("見出しの数が違います: %d -> %d" % (heads(before), heads(after)))
    for w in BANNED:
        if w in after and w not in before:
            problems.append("使わない語が入っています: " + w)
    if len(re.findall(r"<b>", after)) > len(re.findall(r"<b>", before)):
        problems.append("太字が増えています")
    if len(after) < len(before) * 0.55:
        problems.append("本文が短くなりすぎています")
    return problems


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    path = os.path.join(ROOT, args[0])
    apply = "--apply" in sys.argv
    model = default_model()
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    free = "--strict" not in sys.argv    # 既定は自由モード（自分の言葉で書き直す）。--strict でなめらかにするだけ
    tag = "polished"                     # 保存名: xxx.<tag>.txt
    if "--tag" in sys.argv:
        tag = sys.argv[sys.argv.index("--tag") + 1]

    raw = io.open(path, encoding="utf-8").read()
    NL = chr(10)
    sep = NL + "---" + NL
    head, body = raw.split(sep, 1)

    if "--summary-only" in sys.argv:
        summ, usage = write_summary(model, body)
        if not summ:
            sys.exit("[要約NG] " + os.path.basename(path) + "  条件に合う要約が返りませんでした")
        io.open(path, "w", encoding="utf-8", newline=NL).write(replace_summary(head, summ) + sep + body)
        print("[要約] " + os.path.basename(path) + "  " + summ[:60] + "…")
        return

    # 記事の頭にある要約と出典の一覧を「参考資料」として添える（本文には足させない）
    ref = [l for l in head.splitlines() if l.startswith("summary:") or l.startswith("source:")]
    user = body
    if ref:
        user += (NL + NL + "【参考資料】この記事の要約と、本文の元になった出典の一覧です。"
                 "どこから何を取ってきた記事かを知るためのもので、この内容を本文に新しく足してはいけません:" + NL
                 + NL.join(ref))
    # 引用文の一覧を添えて、1文字も変えないよう念を押す
    qs = quotes(body)
    if qs:
        user += (NL + NL + "【確認】次の引用文は、句読点・表記もふくめて1文字も変えずにそのまま残すこと:" + NL
                 + NL.join("「" + q + "」" for q in qs))
    for attempt in (1, 2, 3):
        # HTMLのコードフェンスで返ってきたら外す
        out, usage = call(model, FREE_RULES if free else RULES, user)
        out = re.sub(r"^```(?:html)?\s*", "", out)
        out = re.sub(r"\s*```$", "", out).strip()
        # 太字が増えていたら、元に無い太字だけ外す（Terra は太字を足したがる）
        if len(re.findall(r"<b>", out)) > len(re.findall(r"<b>", body)):
            keep = set(re.findall(r"<b>(.*?)</b>", body))
            out = re.sub(r"<b>(.*?)</b>", lambda m: m.group(0) if m.group(1) in keep else m.group(1), out)
        problems = check(body, out, free)
        tokens = "%s in / %s out" % (usage.get("prompt_tokens", "?"), usage.get("completion_tokens", "?"))
        if not problems:
            break
        if attempt < 3:
            print("[やり直し] " + os.path.basename(path) + "  %d回目は検査に落ちました: " % attempt + " / ".join(problems))
            # 何が悪かったかを具体的に伝えて、もう一度書かせる
            user += (NL + NL + "【前回の問題】前回の書き直しは次の理由で不合格でした。今回は必ず直すこと:" + NL
                     + NL.join("- " + pr for pr in problems))
    if problems:
        print("[差し戻し] " + os.path.basename(path) + "  (" + tokens + ")")
        for p in problems:
            print("   - " + p)
        io.open(path.replace(".txt", ".rejected.txt"), "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        sys.exit(1)

    if free:
        summ, _u = write_summary(model, out)
        if summ:
            head = replace_summary(head, summ)
        else:
            print("   （要約は条件に合わなかったので元のまま）")

    if apply:
        io.open(path, "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        print("[置き換え] " + os.path.basename(path) + "  (" + tokens + ")")
    else:
        p2 = path.replace(".txt", "." + tag + ".txt")
        io.open(p2, "w", encoding="utf-8", newline=NL).write(head + sep + out + NL)
        print("[保存] " + os.path.basename(p2) + "  (" + tokens + ")  検査は通っています。--apply で置き換え")


if __name__ == "__main__":
    main()
