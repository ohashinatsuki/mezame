# -*- coding: utf-8 -*-
"""書き直し前後を1つのファイルにならべる（読みくらべ用）。

    python scripts/compare.py mezame/empath.txt        mezame/empath.くらべ.txt を作る
    python scripts/compare.py --all                     .polished.txt があるものを全部

タグを外した本文を、見出しを ■ にして上下にならべる。
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NL = chr(10)


def plain(path):
    body = io.open(path, encoding="utf-8").read().split(NL + "---" + NL, 1)[1]
    t = re.sub(r"<h[23]>", NL + "■ ", body)
    t = re.sub(r"<li>", "・", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    return t, len(re.sub(r"\s", "", t)), re.findall(r"<h[23]>([^<]+)", body)


def make(src):
    src = os.path.join(ROOT, src)
    pol = src.replace(".txt", ".polished.txt")
    if not os.path.exists(pol):
        print("  書き直しがまだありません: " + os.path.basename(src))
        return
    parts = []
    for label, f in (("前（いまの記事）", src), ("後（書き直し）", pol)):
        t, n, heads = plain(f)
        parts.append("#" * 60 + NL + "# " + label + "  %d文字 / 見出し%d本" % (n, len(heads)) + NL + "#" * 60 + NL + NL + t + NL + NL)
    out = src.replace(".txt", ".くらべ.txt")
    io.open(out, "w", encoding="utf-8", newline=NL).write("".join(parts))
    print("  " + os.path.relpath(out, ROOT))


if "--all" in sys.argv:
    for p in sorted(glob.glob(os.path.join(ROOT, "mezame", "*.polished.txt"))):
        make(os.path.relpath(p.replace(".polished.txt", ".txt"), ROOT))
elif len(sys.argv) > 1:
    make(sys.argv[1])
else:
    sys.exit(__doc__)
