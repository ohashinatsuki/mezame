# -*- coding: utf-8 -*-
"""ウィキメディア・コモンズから画像を取って、項目に紐づける。

    python scripts/get_image.py 一覧 "検索語"          ← 候補を並べるだけ
    python scripts/get_image.py 取得 slug "検索語" 0    ← 0番目の候補を取り込む

取り込むと images/ に保存し、content/<slug>.txt の image と image_credit を
書き換える。権利表示（作者・ライセンス・元ページ）は自動で作る。

商用利用できないライセンス（NC付き、GFDLのみ等）は自動ではじく。
"""
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
CONTENT = os.path.join(ROOT, "content")
UA = {"User-Agent": "occult-taizen/1.0 (https://github.com/ohashinatsuki/occult-taizen)"}

# 商用利用できるライセンスだけを通す
OK = ("public domain", "cc0", "cc by 2.0", "cc by 3.0", "cc by 4.0",
      "cc by-sa 2.0", "cc by-sa 2.5", "cc by-sa 3.0", "cc by-sa 4.0")


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def search(q, n=8):
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
         "&gsrnamespace=6&gsrlimit=%d&gsrsearch=%s&prop=imageinfo"
         "&iiprop=url|extmetadata|mime|size&iiurlwidth=1400" % (n, urllib.parse.quote(q)))
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60))
    out = []
    for p in (d.get("query", {}).get("pages") or {}).values():
        ii = p["imageinfo"][0]
        if not ii.get("mime", "").startswith("image/"):
            continue
        m = ii.get("extmetadata", {})
        lic = strip_html(m.get("LicenseShortName", {}).get("value", ""))
        out.append({
            "title": p["title"][5:],
            "lic": lic,
            "ok": lic.lower() in OK,
            "artist": strip_html(m.get("Artist", {}).get("value", "")) or "作者不明",
            "date": strip_html(m.get("DateTimeOriginal", {}).get("value", "")),
            "page": ii.get("descriptionurl", ""),
            "url": ii.get("thumburl") or ii.get("url"),
        })
    out.sort(key=lambda x: (not x["ok"], "public domain" not in x["lic"].lower()))
    return out


def credit(c):
    parts = [c["artist"]]
    if c["date"]:
        parts.append(c["date"][:40])
    parts.append(c["lic"])
    return "%s ／ ウィキメディア・コモンズ" % "、".join(p for p in parts if p)


def fetch(slug, q, idx=0):
    cands = search(q)
    usable = [c for c in cands if c["ok"]]
    if not usable:
        sys.exit("商用利用できる画像が見つかりませんでした: %s" % q)
    c = usable[idx]
    ext = os.path.splitext(c["title"])[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        ext = ".jpg"
    name = slug + ext
    os.makedirs(IMG, exist_ok=True)
    data = urllib.request.urlopen(
        urllib.request.Request(c["url"], headers=UA), timeout=120).read()
    io.open(os.path.join(IMG, name), "wb").write(data)

    path = os.path.join(CONTENT, slug + ".txt")
    s = io.open(path, encoding="utf-8").read()
    head, body = s.split("\n---\n", 1)
    lines = [l for l in head.split("\n")
             if not l.startswith("image:") and not l.startswith("image_credit:")]
    cr = credit(c) + "（" + c["page"] + "）"
    # 権利表示にリンクを入れる
    cr = "%s ／ %s ／ ウィキメディア・コモンズ" % (c["artist"], c["lic"])
    lines.append("image: " + name)
    lines.append("image_credit: " + cr)
    lines.append("image_source: " + c["page"])
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        "\n".join(lines).rstrip() + "\n---\n" + body)
    print("  取得 %-14s %-46s [%s] %d KB" % (slug, c["title"][:44], c["lic"], len(data) // 1024))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if sys.argv[1] == "一覧":
        for i, c in enumerate(search(sys.argv[2])):
            print("%d %-46s [%s] %s" % (i, c["title"][:44], c["lic"],
                                        "OK" if c["ok"] else "使用不可"))
    else:
        fetch(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0)
