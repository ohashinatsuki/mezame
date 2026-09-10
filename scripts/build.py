# -*- coding: utf-8 -*-
"""めざめ／怪異と謎 サイト生成スクリプト

    python scripts/build.py

作るもの:
  ・各項目のページ            content/*.txt から
  ・トップページ              最新ニュース + 画像カード一覧
  ・最新ニュース              news.json から
  ・五十音索引 / 国別索引 / 分野別索引
  ・sitemap.xml / robots.txt

項目ファイル（content/xxx.txt）の書き方:

    slug: nessie                 ← URLになる英字。必須。重複禁止
    title: ネッシー               ← 項目名。必須
    yomi: ねっしー                ← 五十音索引に使う読み（ひらがな）。必須
    aliases: ネス湖の怪物         ← 別名。任意
    country: イギリス             ← 国別索引。必須
    region: ヨーロッパ            ← 地域。必須
    category: UMA・未確認生物     ← 分野別索引。必須
    summary: 一行の紹介文。必須
    image: nessie.jpg            ← images/ 内のファイル名。任意
    image_credit: 権利表示        ← 画像を使うなら必須
    source: ラベル | https://... | 補足   ← 出典。何行でも書ける。補足は省略可
    ---
    <p>本文をHTMLで書く。文中の出典は <a href="..." target="_blank" rel="noopener">…</a> で。</p>

ニュース（news.json）の書き方:
    {"items":[{"date":"2026-09-08","title":"…","body":"<p>…</p>",
               "sources":[["ラベル","https://…"]]}]}
"""
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
NEWS_PATH = os.path.join(ROOT, "news.json")
SITE = "https://ohashinatsuki.github.io/mezame"
MEZAME = []
SPIRAL = []

REQUIRED = ["slug", "title", "yomi", "country", "region", "category", "summary"]
FEATURES = []

GYO = [
    ("あ", "あいうえおぁぃぅぇぉ"),
    ("か", "かきくけこがぎぐげご"),
    ("さ", "さしすせそざじずぜぞ"),
    ("た", "たちつてとだぢづでどっ"),
    ("な", "なにぬねの"),
    ("は", "はひふへほばびぶべぼぱぴぷぺぽ"),
    ("ま", "まみむめも"),
    ("や", "やゆよゃゅょ"),
    ("ら", "らりるれろ"),
    ("わ", "わをんゐゑ"),
]

CATEGORIES = [
    "UMA・未確認生物", "UFO・UAP", "心霊・幽霊屋敷", "呪い・呪物",
    "古代の謎", "失われた文明", "消失事件", "予言・終末",
    "秘密結社", "妖怪・民間伝承", "超常現象", "都市伝説", "奇妙な場所",
]

REGIONS = ["日本", "アジア", "ヨーロッパ", "北アメリカ", "中南米",
           "アフリカ", "オセアニア", "南極・極地", "海洋", "世界各地"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_entries():
    entries = []
    for fn in sorted(os.listdir(CONTENT)) if os.path.isdir(CONTENT) else []:
        if not fn.endswith(".txt"):
            continue
        raw = io.open(os.path.join(CONTENT, fn), encoding="utf-8").read()
        if "\n---\n" not in raw:
            sys.exit("本文の区切り --- がありません: %s" % fn)
        head, body = raw.split("\n---\n", 1)
        e = {"_file": fn, "sources": []}
        for line in head.strip().split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                sys.exit("front matter の書式が不正です: %s / %s" % (fn, line))
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "source":
                parts = [p.strip() for p in v.split("|")]
                if len(parts) < 2 or not parts[1].startswith("http"):
                    sys.exit("source は「ラベル | URL | 補足」の形式で: %s / %s" % (fn, v))
                e["sources"].append(parts[:3] + [""] * (3 - len(parts)))
            else:
                e[k] = v
        e["body"] = body.strip()
        for k in REQUIRED:
            if not e.get(k):
                sys.exit("%s が足りません: %s" % (k, fn))
        if e.get("image") and not e.get("image_credit"):
            sys.exit("image_credit が足りません: %s" % fn)
        if e["category"] not in CATEGORIES:
            sys.exit("分野名が一覧にありません: %s / %s" % (fn, e["category"]))
        if e["region"] not in REGIONS:
            sys.exit("地域名が一覧にありません: %s / %s" % (fn, e["region"]))
        entries.append(e)
    slugs = [e["slug"] for e in entries]
    dup = {s for s in slugs if slugs.count(s) > 1}
    if dup:
        sys.exit("slug が重複しています: %s" % dup)
    return entries


def load_features():
    """features/*.txt から特集記事を読む。項目ファイルとほぼ同じ書式。
    order（表示順の数字）が必須。"""
    NL = chr(10)
    SEP = NL + "---" + NL
    d = os.path.join(ROOT, "features")
    out = []
    names = sorted(os.listdir(d)) if os.path.isdir(d) else []
    for fn in names:
        if not fn.endswith(".txt"):
            continue
        raw = io.open(os.path.join(d, fn), encoding="utf-8").read()
        if SEP not in raw:
            sys.exit("本文の区切り --- がありません: features/%s" % fn)
        head, body = raw.split(SEP, 1)
        e = {"sources": []}
        for line in head.strip().split(NL):
            if not line.strip() or line.strip().startswith("#"):
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "source":
                parts = [x.strip() for x in v.split("|")]
                e["sources"].append(parts[:3] + [""] * (3 - len(parts)))
            else:
                e[k] = v
        e["body"] = body.strip()
        for k in ("slug", "title", "summary", "order"):
            if not e.get(k):
                sys.exit("%s が足りません: features/%s" % (k, fn))
        if e.get("image") and not e.get("image_credit"):
            sys.exit("image_credit が足りません: features/%s" % fn)
        e["order"] = int(e["order"])
        out.append(e)
    out.sort(key=lambda x: x["order"])
    slugs = [x["slug"] for x in out]
    dup = {x for x in slugs if slugs.count(x) > 1}
    if dup:
        sys.exit("特集の slug が重複しています: %s" % dup)
    return out


def load_news():
    try:
        d = json.load(io.open(NEWS_PATH, encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = d.get("items", [])
    for it in items:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", it.get("date", "")):
            sys.exit("news.json の date が不正です: %s" % it.get("date"))
        if not it.get("title") or not it.get("body"):
            sys.exit("news.json に title か body がありません: %s" % it.get("date"))
    return sorted(items, key=lambda x: x["date"], reverse=True)


def gyo_of(yomi):
    c = yomi[0] if yomi else ""
    for g, chars in GYO:
        if c in chars:
            return g
    return "わ"


HEAD = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canon}">
<meta name="robots" content="index,follow">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{ogtype}">
<meta property="og:locale" content="ja_JP">
{ogimage}<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700;800&family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>

{header}
"""

FOOT = """
{footer}

</body>
</html>
"""

NAVKEYS = ["top", "news", "tokushu", "aiueo", "kuni", "bunya", "about", "spiral"]

# ── セクション定義 ───────────────────────────────────────────
# めざめ（root）と 怪異と謎（/kaii/）。
# めざめ側からは kaii へのリンクを一切出さない。main() の最後で機械的に検査する。

MEZAME_HEADER = """
<header class="masthead">
  <div class="wrap">
    <a class="brand" href="{u}index.html"><span class="b1">めざめのノート</span><span class="b2">AWAKENING NOTES</span></a>
  </div>
</header>

<nav class="mainnav">
  <div class="wrap">
    <a href="{u}index.html"{c_top}>トップ</a>
    <a href="{u}mokuji.html"{c_bunya}>もくじ</a>
    <a href="{u}spiral/index.html"{c_spiral}>スパイラルダイナミクス</a>
    <a href="{u}about.html"{c_about}>このサイトについて</a>
  </div>
</nav>
"""

MEZAME_FOOTER = """
<div class="wrap">
<footer>
  <div class="fnav">
    <a href="{u}index.html">トップ</a>
    <a href="{u}mokuji.html">もくじ</a>
    <a href="{u}spiral/index.html">スパイラルダイナミクス</a>
    <a href="{u}tools/moon-sign.html">月星座を調べる</a>
    <a href="{u}about.html">このサイトについて</a>
    <a href="{u}privacy.html">プライバシーポリシー</a>
  </div>
  <p><b>めざめのノート</b> — ツインレイや月星座などの言葉を、出典とともにたどる資料サイトです。</p>
</footer>
</div>
"""

KAII_HEADER = """
<header class="masthead">
  <div class="wrap">
    <a class="brand" href="{u}index.html"><span class="b1">怪異と謎</span><span class="b2">WORLD MYSTERIES &#183; AN ENCYCLOPEDIA</span></a>
  </div>
</header>

<nav class="mainnav">
  <div class="wrap">
    <a href="index.html"{c_top}>トップ</a>
    <a href="news.html"{c_news}>最新ニュース</a>
    <a href="tokushu.html"{c_tokushu}>特集</a>
    <a href="bunya.html"{c_bunya}>分野別</a>
    <a href="kuni.html"{c_kuni}>国別</a>
    <a href="aiueo.html"{c_aiueo}>五十音索引</a>
    <a href="about.html"{c_about}>このサイトについて</a>
  </div>
</nav>
"""

KAII_FOOTER = """
<div class="wrap">
<footer>
  <div class="fnav">
    <a href="index.html">トップ</a>
    <a href="news.html">最新ニュース</a>
    <a href="tokushu.html">特集</a>
    <a href="bunya.html">分野別索引</a>
    <a href="kuni.html">国別索引</a>
    <a href="aiueo.html">五十音索引</a>
    <a href="about.html">このサイトについて</a>
    <a href="../privacy.html">プライバシーポリシー</a>
  </div>
  <p><b>怪異と謎</b> — 世界の怪異・未確認生物・古代の謎・都市伝説を集めた事典。
  確認されている事実と、語り伝えられている話を、分けて書いています。
  <a href="../index.html">めざめのノート</a> も同じ運営者が書いています。</p>
</footer>
</div>
"""

SEC = {
    "mezame": {"up": "", "u": "", "header": MEZAME_HEADER, "footer": MEZAME_FOOTER},
    "tools":  {"up": "../", "u": "../", "header": MEZAME_HEADER, "footer": MEZAME_FOOTER},
    "spiral": {"up": "../", "u": "../", "header": MEZAME_HEADER, "footer": MEZAME_FOOTER},
    "kaii":   {"up": "../", "u": "", "header": KAII_HEADER, "footer": KAII_FOOTER},
}


def page(title, desc, canon, body, current="", ogtype="article", ogimage="", sec="kaii"):
    cur = {k: (' aria-current="page"' if k == current else "") for k in NAVKEYS}
    d = SEC[sec]
    og = ('<meta property="og:image" content="%s">' % ogimage + chr(10)) if ogimage else ""
    h = HEAD.format(title=esc(title), desc=esc(desc), canon=canon, ogtitle=esc(title),
                    ogtype=ogtype, ogimage=og, up=d["up"],
                    header=d["header"].format(
                        u=d["u"],
                        c_top=cur["top"], c_news=cur["news"], c_tokushu=cur["tokushu"],
                        c_aiueo=cur["aiueo"], c_kuni=cur["kuni"], c_bunya=cur["bunya"],
                        c_about=cur["about"], c_spiral=cur["spiral"]))
    return h + body + FOOT.format(footer=d["footer"].format(u=d["u"]))


def card(e):
    if e.get("image"):
        thumb = '<img src="../images/%s" alt="%s" loading="lazy">' % (esc(e["image"]), esc(e["title"]))
    else:
        thumb = '<span class="noimg">%s</span>' % esc(e["title"])
    return (
        '<a class="card" href="{slug}.html">'
        '<span class="thumb">{thumb}</span>'
        '<span class="cbody"><span class="ctag">{cat}</span>'
        '<span class="ctitle">{title}</span>'
        '<span class="csum">{summary}</span>'
        '<span class="cmeta">{country}</span></span></a>'
    ).format(slug=esc(e["slug"]), thumb=thumb, cat=esc(e["category"]),
             title=esc(e["title"]), summary=esc(e["summary"]), country=esc(e["country"]))


def srclist(sources):
    """出典欄。各項目に id を振って、本文中の（著者, 年）から飛べるようにする。"""
    if not sources:
        return ""
    lis = "".join(
        '<li id="src-{i}"><a href="{u}" target="_blank" rel="noopener">{l}</a>{n}</li>'.format(
            i=i + 1, u=esc(s[1]), l=esc(s[0]),
            n=('<span class="note-s">%s</span>' % esc(s[2])) if s[2] else "")
        for i, s in enumerate(sources))
    return '<h2>出典・参考</h2><ul class="srclist">%s</ul>' % lis


# 本文中の <span class="cite">（著者, 年）</span> を、出典欄への内部リンクにする。
# 「（」の直後から、最初の「,」「，」「 ほか」「 訳」までを著者名とみなし、
# 出典のラベルにその名前が含まれるものを探して結びつける。
CITE_RE = re.compile(r'<span class="cite">（([^）]+)）</span>')


def link_cites(body, sources):
    if not sources:
        return body

    def key_names(inner):
        """（Ford ほか, 2018／Barks 訳, 2004）から、照合に使う名前を取り出す"""
        inner = html.unescape(inner)
        out = []
        for chunk in re.split(r"[／/]", inner):
            m = re.match(r"\s*([^,，]+)", chunk)
            if not m:
                continue
            name = m.group(1)
            name = re.sub(r"\s*(ほか|訳|編|監修|ら)\s*$", "", name).strip()
            if name:
                out.append(name)
        return out

    def repl(m):
        inner = m.group(1)
        for name in key_names(inner):
            for i, s in enumerate(sources):
                if name and name.lower() in s[0].lower():
                    return ('<a class="cite" href="#src-%d">（%s）</a>'
                            % (i + 1, esc(inner)))
        # 見つからなければ、そのまま（リンクなし）
        return m.group(0)

    return CITE_RE.sub(repl, body)


def write(path, text):
    full = os.path.join(ROOT, path)
    d = os.path.dirname(full)
    if d:
        os.makedirs(d, exist_ok=True)
    io.open(full, "w", encoding="utf-8", newline="\n").write(text)


def build_entry(e, entries):
    same = [x for x in entries if x["slug"] != e["slug"]
            and (x["category"] == e["category"] or x["country"] == e["country"])][:6]
    rel = ('<h2>関連する項目</h2><div class="grid small">%s</div>'
           % "".join(card(x) for x in same)) if same else ""
    img = ""
    if e.get("image"):
        cap = esc(e["image_credit"])
        if e.get("image_source"):
            cap += ('　<a href="%s" target="_blank" rel="noopener">元ページ</a>'
                    % esc(e["image_source"]))
        img = ('<figure class="hero"><img src="../images/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>'
               % (esc(e["image"]), esc(e["title"]), cap))
    alias = ('<p class="alias">別名: %s</p>' % esc(e["aliases"])) if e.get("aliases") else ""
    body = """
<main class="wrap">
<article class="entry">
  <p class="crumb"><a href="bunya.html">{cat}</a> ／ <a href="kuni.html">{country}</a></p>
  <h1>{title}</h1>
  {alias}
  <p class="lead">{summary}</p>
  {img}
  {content}
  {src}
  {rel}
</article>
</main>
""".format(cat=esc(e["category"]), country=esc(e["country"]), title=esc(e["title"]),
           alias=alias, summary=esc(e["summary"]), img=img,
           content=link_cites(e["body"], e["sources"]),
           src=srclist(e["sources"]), rel=rel)
    ogimg = "%s/images/%s" % (SITE, e["image"]) if e.get("image") else ""
    write("kaii/%s.html" % e["slug"],
          page("%s — 怪異と謎" % e["title"], e["summary"],
               "%s/%s.html" % (SITE, e["slug"]), body, ogimage=ogimg))


def jdate(d):
    y, m, day = d.split("-")
    return "%s年%s月%s日" % (y, int(m), int(day))


def news_block(items, limit=None):
    use = items[:limit] if limit else items
    out = []
    for it in use:
        srcs = ""
        if it.get("sources"):
            srcs = ('<ul class="srclist">%s</ul>' % "".join(
                '<li><a href="%s" target="_blank" rel="noopener">%s</a></li>'
                % (esc(u), esc(l)) for l, u in it["sources"]))
        out.append(
            '<article class="newsitem" id="n-{d}"><p class="ndate">{jd}</p>'
            '<h3>{t}</h3>{b}{s}</article>'.format(
                d=esc(it["date"]), jd=jdate(it["date"]), t=esc(it["title"]),
                b=it["body"], s=srcs))
    return "".join(out)


def build_news(items):
    body = """
<main class="wrap">
<article class="entry">
  <h1>オカルト最新ニュース</h1>
  <p class="lead">世界のオカルト・未解明現象に関する出来事を、週に一度まとめています。
  出所のはっきりした報道や発表だけを扱い、うわさ話は載せません。</p>
  {items}
</article>
</main>
""".format(items=news_block(items) or "<p>まだ記事がありません。</p>")
    write("kaii/news.html",
          page("最新ニュース — 怪異と謎",
               "世界のオカルト・未解明現象に関する出来事を週に一度まとめています。UFO・UAPの公的発表、考古学の新発見、未確認生物の目撃報道など。",
               SITE + "/kaii/news.html", body, current="news", ogtype="website"))


def build_top(entries, news):
    latest = ""
    toku = ""
    if FEATURES:
        toku = """
  <section class="tokuband">
    <div class="nbhead"><h2>特集</h2><a href="tokushu.html">すべて見る &#8594;</a></div>
    <div class="grid">{cards}</div>
  </section>
""".format(cards="".join(fcard(f) for f in FEATURES[:3]))
    if news:
        latest = """
  <section class="newsband">
    <div class="nbhead"><h2>最新ニュース</h2><a href="news.html">すべて見る →</a></div>
    {items}
  </section>
""".format(items=news_block(news, limit=3))
    body = """
<main class="wrap">
  <section class="hero-copy">
    <h1>怪異と謎</h1>
    <p>世界じゅうの怪異、未確認生物、古代の謎、消えた文明、都市伝説を集めた事典です。
    現在 <b>{n}項目</b>、20か国・13分野。<a href="bunya.html">分野</a>・<a href="kuni.html">国</a>・<a href="aiueo.html">五十音</a>から引けます。</p>
  </section>
  {latest}
  {toku}
  <section>
    <h2 class="sechead">事典</h2>
    <div class="grid">{cards}</div>
  </section>
</main>
""".format(n=len(entries), latest=latest, toku=toku,
           cards="".join(card(e) for e in entries))
    write("kaii/index.html",
          page("怪異と謎 — 世界の怪異と未確認現象の事典",
               "世界じゅうの怪異、未確認生物、古代の謎、消えた文明、都市伝説を集めた事典。%d項目を五十音・国別・分野別から引けます。オカルト最新ニュースも週1で更新。" % len(entries),
               SITE + "/kaii/", body, current="top", ogtype="website"))


def build_aiueo(entries):
    rows, nav = [], []
    for g, _ in GYO:
        items = sorted([e for e in entries if gyo_of(e["yomi"]) == g], key=lambda x: x["yomi"])
        if not items:
            continue
        nav.append('<a href="#g-%s">%s</a>' % (g, g))
        lis = "".join(
            '<li><a href="{s}.html">{t}</a><span class="y">{y}</span>'
            '<span class="k">{c}</span></li>'.format(
                s=esc(e["slug"]), t=esc(e["title"]), y=esc(e["yomi"]), c=esc(e["category"]))
            for e in items)
        rows.append('<section class="gyo" id="g-%s"><h2>%s行</h2><ul class="dict">%s</ul></section>'
                    % (g, g, lis))
    body = """
<main class="wrap">
<article>
  <h1>五十音索引</h1>
  <p class="lead">項目名の読みの順に並べています。全{n}項目。</p>
  <div class="gyonav">{nav}</div>
  {rows}
</article>
</main>
""".format(n=len(entries), nav="".join(nav), rows="".join(rows))
    write("kaii/aiueo.html", page("五十音索引 — 怪異と謎",
                             "怪異と謎の全項目を、読みの五十音順に並べた索引です。",
                             SITE + "/kaii/aiueo.html", body, current="aiueo", ogtype="website"))


def build_group(entries, key, order, fname, h1, desc, current):
    groups = {}
    for e in entries:
        groups.setdefault(e[key], []).append(e)
    keys = [k for k in order if k in groups] + sorted(k for k in groups if k not in order)
    nav, secs = [], []
    for i, k in enumerate(keys):
        items = sorted(groups[k], key=lambda x: x["yomi"])
        nav.append('<a href="#g%d">%s<span>%d</span></a>' % (i, esc(k), len(items)))
        secs.append('<section class="gyo" id="g%d"><h2>%s<span class="cnt">%d項目</span></h2>'
                    '<div class="grid small">%s</div></section>'
                    % (i, esc(k), len(items), "".join(card(e) for e in items)))
    body = """
<main class="wrap">
<article>
  <h1>{h1}</h1>
  <p class="lead">{desc}</p>
  <div class="gyonav wide">{nav}</div>
  {secs}
</article>
</main>
""".format(h1=esc(h1), desc=esc(desc), nav="".join(nav), secs="".join(secs))
    write("kaii/" + fname, page("%s — 怪異と謎" % h1, desc,
                                "%s/kaii/%s" % (SITE, fname),
                                body, current=current, ogtype="website"))


def build_feature(f, entries):
    img = ""
    if f.get("image"):
        cap = esc(f["image_credit"])
        if f.get("image_source"):
            cap += ('　<a href="%s" target="_blank" rel="noopener">元ページ</a>'
                    % esc(f["image_source"]))
        img = ('<figure class="hero"><img src="../images/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>'
               % (esc(f["image"]), esc(f["title"]), cap))
    body = """
<main class="wrap">
<article class="entry">
  <p class="crumb"><a href="tokushu.html">特集</a></p>
  <h1>{title}</h1>
  <p class="lead">{summary}</p>
  {img}
  {content}
  {src}
</article>
</main>
""".format(title=esc(f["title"]), summary=esc(f["summary"]), img=img,
           content=link_cites(f["body"], f["sources"]), src=srclist(f["sources"]))
    ogimg = "%s/images/%s" % (SITE, f["image"]) if f.get("image") else ""
    write("kaii/%s.html" % f["slug"],
          page("%s — 怪異と謎" % f["title"], f["summary"],
               "%s/%s.html" % (SITE, f["slug"]), body, current="tokushu", ogimage=ogimg))


def fcard(f):
    if f.get("image"):
        thumb = '<img src="../images/%s" alt="%s" loading="lazy">' % (esc(f["image"]), esc(f["title"]))
    else:
        thumb = '<span class="noimg">%s</span>' % esc(f["title"])
    return ('<a class="card" href="{slug}.html"><span class="thumb">{thumb}</span>'
            '<span class="cbody"><span class="ctag toku">特集</span>'
            '<span class="ctitle">{title}</span>'
            '<span class="csum">{summary}</span></span></a>').format(
        slug=esc(f["slug"]), thumb=thumb, title=esc(f["title"]), summary=esc(f["summary"]))


def build_tokushu(features):
    body = """
<main class="wrap">
<article>
  <h1>特集</h1>
  <p class="lead">事典の項目を横につないで読む記事です。ばらばらに見える怪異のあいだに、
  同じ形が何度も現れます。ここでも、確認されていることと語られていることは分けて書きます。</p>
  <div class="grid">{cards}</div>
</article>
</main>
""".format(cards="".join(fcard(f) for f in features) or "<p>準備中です。</p>")
    write("kaii/tokushu.html",
          page("特集 — 怪異と謎",
               "怪異と謎の特集記事。怪異はなぜ危険な場所に現れるのか、作り物と判明しても話が残るのはなぜか、本当に説明がつかないものは何か。事典60項目を横断して読み解きます。",
               SITE + "/kaii/tokushu.html", body, current="tokushu", ogtype="website"))


def load_mezame():
    """mezame/*.txt を読む。めざめ側のことばの記事。

        slug: moon-sign          URLになる英字。必須
        title: 月星座             必須
        en: moon sign            英語のもとの言い方。任意
        yomi: つきせいざ          並び順に使う。必須
        tags: 占星術              任意
        summary: 一行の説明。必須
        image / image_credit / image_source   任意
        source: ラベル | URL | 補足    何行でも
        ---
        本文HTML
    """
    NL = chr(10)
    SEP = NL + "---" + NL
    d = os.path.join(ROOT, "mezame")
    out = []
    names = sorted(os.listdir(d)) if os.path.isdir(d) else []
    for fn in names:
        if not fn.endswith(".txt") or fn.endswith((".polished.txt", ".rejected.txt",
                                                   ".draft.txt", ".gpt.txt")):
            continue
        raw = io.open(os.path.join(d, fn), encoding="utf-8").read()
        if SEP not in raw:
            sys.exit("本文の区切り --- がありません: mezame/%s" % fn)
        head, body = raw.split(SEP, 1)
        e = {"sources": []}
        for line in head.strip().split(NL):
            if not line.strip() or line.strip().startswith("#"):
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "source":
                parts = [x.strip() for x in v.split("|")]
                e["sources"].append(parts[:3] + [""] * (3 - len(parts)))
            else:
                e[k] = v
        e["body"] = body.strip()
        for k in ("slug", "title", "yomi", "summary"):
            if not e.get(k):
                sys.exit("%s が足りません: mezame/%s" % (k, fn))
        if e.get("image") and not e.get("image_credit"):
            sys.exit("image_credit が足りません: mezame/%s" % fn)
        out.append(e)
    out.sort(key=lambda x: x["yomi"])
    slugs = [x["slug"] for x in out]
    dup = {x for x in slugs if slugs.count(x) > 1}
    if dup:
        sys.exit("めざめの slug が重複しています: %s" % dup)
    return out


def mcard(e):
    if e.get("image"):
        thumb = '<img src="images/%s" alt="%s" loading="lazy">' % (esc(e["image"]), esc(e["title"]))
    else:
        thumb = '<span class="noimg">%s</span>' % esc(e["title"])
    return ('<a class="card" href="{slug}.html"><span class="thumb">{thumb}</span>'
            '<span class="cbody"><span class="ctag">{en}</span>'
            '<span class="ctitle">{title}</span>'
            '<span class="csum">{summary}</span></span></a>').format(
        slug=esc(e["slug"]), thumb=thumb, en=esc(e.get("en", "") or e.get("tags", "")),
        title=esc(e["title"]), summary=esc(e["summary"]))


def build_mezame_entry(e, entries):
    img = ""
    if e.get("image"):
        cap = esc(e["image_credit"])
        if e.get("image_source"):
            cap += ('　<a href="%s" target="_blank" rel="noopener">元ページ</a>'
                    % esc(e["image_source"]))
        img = ('<figure class="hero"><img src="images/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>'
               % (esc(e["image"]), esc(e["title"]), cap))
    rel = [x for x in entries if x["slug"] != e["slug"]][:6]
    relhtml = ('<h2>関連することば</h2><div class="grid small">%s</div>'
               % "".join(mcard(x) for x in rel)) if rel else ""
    en = ('<p class="crumb">%s</p>' % esc(e["en"])) if e.get("en") else ""
    body = """
<main class="wrap">
<article class="entry">
  {en}
  <h1>{title}</h1>
  <p class="lead">{summary}</p>
  {img}
  {content}
  {src}
  {rel}
</article>
</main>
""".format(en=en, title=esc(e["title"]), summary=esc(e["summary"]), img=img,
           content=link_cites(e["body"], e["sources"]), src=srclist(e["sources"]), rel=relhtml)
    ogimg = "%s/images/%s" % (SITE, e["image"]) if e.get("image") else ""
    write("%s.html" % e["slug"],
          page("%s — めざめのノート" % e["title"], e["summary"],
               "%s/%s.html" % (SITE, e["slug"]), body,
               current="", ogimage=ogimg, sec="mezame"))


def build_mokuji(entries):
    body = """
<main class="wrap">
<article>
  <h1>もくじ</h1>
  <p class="lead">いま書いてあるものの一覧です。</p>
  <p class="hint">計算するもの：<a href="tools/moon-sign.html">月星座を調べる</a></p>
  <div class="grid">{cards}</div>
</article>
</main>
""".format(cards="".join(mcard(e) for e in entries) or "<p>準備中です。</p>")
    write("mokuji.html",
          page("もくじ — めざめのノート",
               "めざめのノートに書いてあるものの一覧。ツインレイ、エンパス、月星座。",
               SITE + "/mokuji.html", body, current="bunya", ogtype="website", sec="mezame"))


def build_mezame_top(entries):
    body = """
<main class="wrap">
  <section class="hero-copy">
    <h1>めざめのノート</h1>
    <p class="invite">ツインレイなどの言葉を、出典とともにたどる。</p>
    <p>ツインレイなどの言葉を、出典とともにたどる資料サイトです。</p>
  </section>
  <section>
    <div class="grid">{cards}</div>
  </section>
</main>
""".format(cards="".join(mcard(e) for e in entries) or
           "<p>いま準備しています。もう少しお待ちください。</p>")
    write("index.html",
          page("めざめのノート — ツインレイ・エンパス・月星座",
               "ツインレイ、エンパス、月星座。さまざまな言葉について、誰がどのように語っているかを"
               "資料でたどり、出典とともに紹介するノートです。意味や背景を静かに確かめるために。",
               SITE + "/", body, current="top", ogtype="website", sec="mezame"))


def load_spiral():
    """spiral/*.txt を読む。スパイラルダイナミクスのタブ。前書きは mezame と同じで、
    order: 1 という行で順番を決める（index → 序論 → 各段階 → 応用と批判）。"""
    NL = chr(10)
    SEP = NL + "---" + NL
    d = os.path.join(ROOT, "spiral")
    out = []
    names = sorted(os.listdir(d)) if os.path.isdir(d) else []
    for fn in names:
        if not fn.endswith(".txt"):
            continue
        raw = io.open(os.path.join(d, fn), encoding="utf-8").read()
        if SEP not in raw:
            sys.exit("本文の区切り --- がありません: spiral/%s" % fn)
        head, body = raw.split(SEP, 1)
        e = {"sources": []}
        for line in head.strip().split(NL):
            if not line.strip() or line.strip().startswith("#"):
                continue
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            if k == "source":
                parts = [x.strip() for x in v.split("|")]
                e["sources"].append(parts[:3] + [""] * (3 - len(parts)))
            else:
                e[k] = v
        e["body"] = body.strip()
        for k in ("slug", "title", "order", "summary"):
            if not e.get(k):
                sys.exit("%s が足りません: spiral/%s" % (k, fn))
        if e.get("image") and not e.get("image_credit"):
            sys.exit("image_credit が足りません: spiral/%s" % fn)
        e["order"] = int(e["order"])
        out.append(e)
    out.sort(key=lambda x: x["order"])
    slugs = [x["slug"] for x in out]
    dup = {x for x in slugs if slugs.count(x) > 1}
    if dup:
        sys.exit("spiral の slug が重複しています: %s" % dup)
    return out


def scard(e):
    if e.get("image"):
        thumb = '<img src="../images/%s" alt="%s" loading="lazy">' % (esc(e["image"]), esc(e["title"]))
    else:
        thumb = '<span class="noimg">%s</span>' % esc(e["title"])
    return ('<a class="card" href="{slug}.html"><span class="thumb">{thumb}</span>'
            '<span class="cbody"><span class="ctag">{n}</span>'
            '<span class="ctitle">{title}</span>'
            '<span class="csum">{summary}</span></span></a>').format(
        slug=esc(e["slug"]), thumb=thumb, n=esc(e.get("en", "") or ("%d" % e["order"])),
        title=esc(e["title"]), summary=esc(e["summary"]))


def build_spiral_entry(e, entries):
    img = ""
    if e.get("image"):
        cap = esc(e["image_credit"])
        if e.get("image_source"):
            cap += ('　<a href="%s" target="_blank" rel="noopener">元ページ</a>'
                    % esc(e["image_source"]))
        img = ('<figure class="hero"><img src="../images/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>'
               % (esc(e["image"]), esc(e["title"]), cap))
    i = entries.index(e)
    prv = entries[i - 1] if i > 0 else None
    nxt = entries[i + 1] if i + 1 < len(entries) else None
    pn = '<div class="prevnext">'
    pn += ('<a class="prev" href="%s.html">← %s</a>' % (esc(prv["slug"]), esc(prv["title"]))) if prv else '<span></span>'
    pn += ('<a class="next" href="%s.html">%s →</a>' % (esc(nxt["slug"]), esc(nxt["title"]))) if nxt else '<span></span>'
    pn += '</div>'
    crumb = '<p class="crumb"><a href="index.html">スパイラルダイナミクス</a> › %d / %d</p>' % (e["order"], len(entries))
    body = """
<main class="wrap">
<article class="entry">
  {crumb}
  <h1>{title}</h1>
  <p class="lead">{summary}</p>
  {img}
  {content}
  {src}
  {pn}
</article>
</main>
""".format(crumb=crumb, title=esc(e["title"]), summary=esc(e["summary"]), img=img,
           content=link_cites(e["body"], e["sources"]), src=srclist(e["sources"]), pn=pn)
    ogimg = "%s/images/%s" % (SITE, e["image"]) if e.get("image") else ""
    write(os.path.join("spiral", "%s.html" % e["slug"]),
          page("%s — スパイラルダイナミクス" % e["title"], e["summary"],
               "%s/spiral/%s.html" % (SITE, e["slug"]), body,
               current="spiral", ogimage=ogimg, sec="spiral"))


def build_spiral_index(entries):
    body = """
<main class="wrap">
  <section class="hero-copy">
    <h1>スパイラルダイナミクス</h1>
    <p class="invite">人の価値観が、どんな順番で変わっていくかを描いた地図。</p>
    <p>心理学者クレア・グレイヴスが1960〜70年代に集めた資料から作られ、1996年にベックとコーワンが本にした理論を、順番に読めるようにしています。段階は人を格付けするものではなく、その人がいま置かれている条件への答え方だ、というのがこの理論の出発点です。上から順にお読みください。</p>
  </section>
  <section>
    <div class="grid">{cards}</div>
  </section>
</main>
""".format(cards="".join(scard(e) for e in entries) or
           "<p>いま準備しています。もう少しお待ちください。</p>")
    write(os.path.join("spiral", "index.html"),
          page("スパイラルダイナミクス — めざめのノート",
               "クレア・グレイヴスの理論から生まれた、人の価値観の発達段階の地図。序論、8つの段階、応用と批判。",
               SITE + "/spiral/", body, current="spiral", ogtype="website", sec="spiral"))


def check_walls():
    """めざめ側のページから kaii/ へのリンクが1本でも出ていたら止める。"""
    import glob
    bad = []
    files = (glob.glob(os.path.join(ROOT, "*.html"))
             + glob.glob(os.path.join(ROOT, "tools", "*.html"))
             + glob.glob(os.path.join(ROOT, "spiral", "*.html")))
    for fp in files:
        t = io.open(fp, encoding="utf-8").read()
        for m in re.findall(r'href="([^"]+)"', t):
            if "kaii/" in m:
                bad.append((os.path.basename(fp), m))
    if bad:
        for f, h in bad:
            print("  %s -> %s" % (f, h))
        sys.exit("[停止] めざめ側から怪異へのリンクが見つかりました。上を直してください。")
    print("壁の検査: めざめ側から怪異へのリンクは 0 本")


def build_sitemap(entries):
    urls = (["", "mokuji.html", "about.html", "privacy.html"]
            + ["%s.html" % e["slug"] for e in MEZAME]
            + ["spiral/"] + ["spiral/%s.html" % e["slug"] for e in SPIRAL]
            + ["kaii/", "kaii/news.html", "kaii/tokushu.html", "kaii/aiueo.html",
               "kaii/kuni.html", "kaii/bunya.html", "kaii/about.html"]
            + ["kaii/%s.html" % e["slug"] for e in entries]
            + ["kaii/%s.html" % f["slug"] for f in FEATURES])
    rows = "".join(
        "  <url><loc>%s/%s</loc><changefreq>%s</changefreq><priority>%s</priority></url>\n"
        % (SITE, u,
           "weekly" if u in ("", "mokuji.html", "kaii/", "kaii/news.html") else "monthly",
           "1.0" if u == "" else ("0.9" if u in ("mokuji.html", "kaii/") else "0.7"))
        for u in urls)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % rows)
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


def main():
    entries = load_entries()
    if not entries:
        sys.exit("content/ に項目がありません")
    news = load_news()
    global FEATURES, MEZAME, SPIRAL
    FEATURES = load_features()
    MEZAME = load_mezame()
    SPIRAL = load_spiral()
    for e in MEZAME:
        build_mezame_entry(e, MEZAME)
    build_mokuji(MEZAME)
    build_mezame_top(MEZAME)
    for e in SPIRAL:
        build_spiral_entry(e, SPIRAL)
    build_spiral_index(SPIRAL)
    for f in FEATURES:
        build_feature(f, entries)
    build_tokushu(FEATURES)
    for e in entries:
        build_entry(e, entries)
    build_top(entries, news)
    build_news(news)
    build_aiueo(entries)
    build_group(entries, "country", [], "kuni.html", "国別索引",
                "項目を国・地域ごとにまとめています。", "kuni")
    build_group(entries, "category", CATEGORIES, "bunya.html", "分野別索引",
                "項目を13の分野に分けています。", "bunya")
    build_sitemap(entries)
    noimg = [e["title"] for e in entries if not e.get("image")]
    nosrc = [e["title"] for e in entries if not e["sources"]]
    check_walls()
    print("生成完了: めざめ%d / スパイラル%d / 怪異%d項目 / 特集%d本 / ニュース%d件"
          % (len(MEZAME), len(SPIRAL), len(entries), len(FEATURES), len(news)))
    print("画像なし: %d件" % len(noimg))
    if nosrc:
        print("[注意] 出典リンクなし: " + "、".join(nosrc))


main()
