# -*- coding: utf-8 -*-
"""世界オカルト大全 サイト生成スクリプト

content/ に置いた項目ファイルから、
  ・各項目のページ
  ・トップページ（画像カード一覧）
  ・五十音索引 / 国別索引 / 分野別索引
  ・sitemap.xml
をまとめて作る。項目を足したら、このスクリプトを実行し直すだけでよい。

    python scripts/build.py

項目ファイルの書き方（content/xxx.txt）:

    slug: nessie                    ← URLになる英字。必須。重複禁止
    title: ネッシー                  ← 項目名。必須
    yomi: ねっしー                   ← 五十音索引に使う読み。必須（ひらがな）
    aliases: ネス湖の怪物            ← 別名。任意（読点区切り）
    country: イギリス                ← 国別索引に使う。必須
    region: ヨーロッパ               ← 地域。必須
    category: UMA・未確認生物        ← 分野別索引に使う。必須
    summary: 一行の紹介文。カードに出る。必須
    image: nessie.jpg               ← images/ 内のファイル名。任意
    image_credit: 出典と権利表示      ← 画像を使うなら必須
    ---
    <p>本文をHTMLで書く。</p>
"""
import html
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
SITE = "https://ohashinatsuki.github.io/occult-taizen"

REQUIRED = ["slug", "title", "yomi", "country", "region", "category", "summary"]

# 五十音索引の行分け
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
    if not os.path.isdir(CONTENT):
        return entries
    for fn in sorted(os.listdir(CONTENT)):
        if not fn.endswith(".txt"):
            continue
        raw = io.open(os.path.join(CONTENT, fn), encoding="utf-8").read()
        if "\n---\n" not in raw:
            sys.exit("本文の区切り --- がありません: %s" % fn)
        head, body = raw.split("\n---\n", 1)
        e = {"_file": fn}
        for line in head.strip().split("\n"):
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                sys.exit("front matter の書式が不正です: %s / %s" % (fn, line))
            k, v = line.split(":", 1)
            e[k.strip()] = v.strip()
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
<link rel="stylesheet" href="{base}style.css">
</head>
<body>

<header class="masthead">
  <div class="wrap">
    <a class="brand" href="{base}"><span class="b1">世界オカルト大全</span><span class="b2">WORLD OCCULT ENCYCLOPEDIA</span></a>
  </div>
</header>

<nav class="mainnav">
  <div class="wrap">
    <a href="{base}"{c_top}>トップ</a>
    <a href="{base}aiueo.html"{c_aiueo}>五十音索引</a>
    <a href="{base}kuni.html"{c_kuni}>国別</a>
    <a href="{base}bunya.html"{c_bunya}>分野別</a>
    <a href="{base}about.html"{c_about}>このサイトについて</a>
  </div>
</nav>
"""

FOOT = """
<div class="wrap">
<footer>
  <div class="fnav">
    <a href="{base}">トップ</a>
    <a href="{base}aiueo.html">五十音索引</a>
    <a href="{base}kuni.html">国別索引</a>
    <a href="{base}bunya.html">分野別索引</a>
    <a href="{base}about.html">このサイトについて</a>
    <a href="{base}privacy.html">プライバシーポリシー</a>
  </div>
  <p><b>世界オカルト大全</b> — 世界の怪異・未確認生物・古代の謎・都市伝説を集めた事典。
  確認されている事実と、語り伝えられている話を、分けて書いています。</p>
</footer>
</div>

</body>
</html>
"""


def page(title, desc, canon, body, base="", current="", ogtype="article", ogimage=""):
    cur = {k: (' aria-current="page"' if k == current else "")
           for k in ["top", "aiueo", "kuni", "bunya", "about"]}
    og = ('<meta property="og:image" content="%s">\n' % ogimage) if ogimage else ""
    h = HEAD.format(title=esc(title), desc=esc(desc), canon=canon, ogtitle=esc(title),
                    ogtype=ogtype, ogimage=og, base=base,
                    c_top=cur["top"], c_aiueo=cur["aiueo"], c_kuni=cur["kuni"],
                    c_bunya=cur["bunya"], c_about=cur["about"])
    return h + body + FOOT.format(base=base)


def card(e):
    """トップページと索引で使う画像カード。画像がなければ文字だけのタイルにする。"""
    if e.get("image"):
        thumb = '<img src="images/%s" alt="%s" loading="lazy">' % (esc(e["image"]), esc(e["title"]))
    else:
        thumb = '<span class="noimg">%s</span>' % esc(e["title"])
    return (
        '<a class="card" href="{slug}.html">'
        '<span class="thumb">{thumb}</span>'
        '<span class="cbody">'
        '<span class="ctag">{cat}</span>'
        '<span class="ctitle">{title}</span>'
        '<span class="csum">{summary}</span>'
        '<span class="cmeta">{country}</span>'
        '</span></a>'
    ).format(slug=esc(e["slug"]), thumb=thumb, cat=esc(e["category"]),
             title=esc(e["title"]), summary=esc(e["summary"]), country=esc(e["country"]))


def write(path, text):
    io.open(os.path.join(ROOT, path), "w", encoding="utf-8", newline="\n").write(text)


def build_entry(e, entries):
    same = [x for x in entries
            if x["slug"] != e["slug"] and
            (x["category"] == e["category"] or x["country"] == e["country"])][:6]
    rel = ""
    if same:
        rel = ('<h2>関連する項目</h2><div class="grid small">'
               + "".join(card(x) for x in same) + "</div>")
    img = ""
    if e.get("image"):
        img = ('<figure class="hero"><img src="images/%s" alt="%s">'
               '<figcaption>%s</figcaption></figure>'
               % (esc(e["image"]), esc(e["title"]), esc(e["image_credit"])))
    alias = ""
    if e.get("aliases"):
        alias = '<p class="alias">別名: %s</p>' % esc(e["aliases"])
    body = """
<main class="wrap">
<article class="entry">
  <p class="crumb"><a href="bunya.html">{cat}</a> ／ <a href="kuni.html">{country}</a></p>
  <h1>{title}</h1>
  {alias}
  <p class="lead">{summary}</p>
  {img}
  {content}
  {rel}
</article>
</main>
""".format(cat=esc(e["category"]), country=esc(e["country"]), title=esc(e["title"]),
           alias=alias, summary=esc(e["summary"]), img=img, content=e["body"], rel=rel)
    ogimg = "%s/images/%s" % (SITE, e["image"]) if e.get("image") else ""
    write("%s.html" % e["slug"],
          page("%s — 世界オカルト大全" % e["title"], e["summary"],
               "%s/%s.html" % (SITE, e["slug"]), body, ogimage=ogimg))


def build_top(entries):
    cards = "".join(card(e) for e in entries)
    body = """
<main class="wrap">
  <section class="hero-copy">
    <h1>世界オカルト大全</h1>
    <p>世界じゅうの怪異、未確認生物、古代の謎、消えた文明、都市伝説を集めた事典です。
    現在 <b>{n}項目</b>。<a href="aiueo.html">五十音</a>・<a href="kuni.html">国</a>・<a href="bunya.html">分野</a>から引けます。</p>
  </section>
  <div class="grid">{cards}</div>
</main>
""".format(n=len(entries), cards=cards)
    write("index.html",
          page("世界オカルト大全 — 世界の怪異と未確認現象の事典",
               "世界じゅうの怪異、未確認生物、古代の謎、消えた文明、都市伝説を集めた事典。%d項目を五十音・国別・分野別から引けます。" % len(entries),
               SITE + "/", body, current="top", ogtype="website"))


def build_aiueo(entries):
    rows = []
    nav = []
    for g, chars in GYO:
        items = sorted([e for e in entries if gyo_of(e["yomi"]) == g],
                       key=lambda x: x["yomi"])
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
    write("aiueo.html",
          page("五十音索引 — 世界オカルト大全",
               "世界オカルト大全の全項目を、読みの五十音順に並べた索引です。",
               SITE + "/aiueo.html", body, current="aiueo", ogtype="website"))


def build_group(entries, key, order, fname, h1, desc, current):
    secs = []
    nav = []
    groups = {}
    for e in entries:
        groups.setdefault(e[key], []).append(e)
    keys = [k for k in order if k in groups] + sorted(k for k in groups if k not in order)
    for k in keys:
        items = sorted(groups[k], key=lambda x: x["yomi"])
        anchor = "g%d" % keys.index(k)
        nav.append('<a href="#%s">%s<span>%d</span></a>' % (anchor, esc(k), len(items)))
        secs.append('<section class="gyo" id="%s"><h2>%s<span class="cnt">%d項目</span></h2>'
                    '<div class="grid small">%s</div></section>'
                    % (anchor, esc(k), len(items), "".join(card(e) for e in items)))
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
    write(fname, page("%s — 世界オカルト大全" % h1, desc,
                      "%s/%s" % (SITE, fname), body, current=current, ogtype="website"))


def build_sitemap(entries):
    urls = ["", "aiueo.html", "kuni.html", "bunya.html", "about.html", "privacy.html"]
    urls += ["%s.html" % e["slug"] for e in entries]
    rows = "".join(
        "  <url><loc>%s/%s</loc><changefreq>%s</changefreq><priority>%s</priority></url>\n"
        % (SITE, u, "weekly" if u in ("", "aiueo.html", "kuni.html", "bunya.html") else "monthly",
           "1.0" if u == "" else "0.7")
        for u in urls)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % rows)
    write("robots.txt", "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE)


def main():
    entries = load_entries()
    if not entries:
        sys.exit("content/ に項目がありません")
    for e in entries:
        build_entry(e, entries)
    build_top(entries)
    build_aiueo(entries)
    build_group(entries, "country", [], "kuni.html", "国別索引",
                "項目を国・地域ごとにまとめています。", "kuni")
    build_group(entries, "category", CATEGORIES, "bunya.html", "分野別索引",
                "項目を13の分野に分けています。", "bunya")
    build_sitemap(entries)
    noimg = [e["title"] for e in entries if not e.get("image")]
    print("生成完了: %d項目 + 索引3枚" % len(entries))
    print("画像なしの項目: %d件" % len(noimg))
    if noimg:
        print("  " + "、".join(noimg[:12]) + ("…" if len(noimg) > 12 else ""))


main()
