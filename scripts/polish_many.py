# -*- coding: utf-8 -*-
"""複数の記事をまとめて書き直す（1本ずつ順に polish.py を呼ぶ）。

    python scripts/polish_many.py aura chakra dark-night      slug を並べる
    python scripts/polish_many.py --next 10                   まだ書き直していないものを先頭から10本

進み具合は mezame/_書き直しログ.txt に書く。終わると compare.py --all でくらべファイルも作る。
"""
import glob
import io
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "_再挑戦ログ.txt")
NL = chr(10)


def log(msg):
    line = time.strftime("%H:%M ") + msg
    print(line)
    io.open(LOG, "a", encoding="utf-8", newline=NL).write(line + NL)


def is_source(p):
    b = os.path.basename(p)
    return not any(x in b for x in (".draft.", ".polished.", ".rejected.", "-free.", "くらべ", "_書き直し"))


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "--next":
        n = int(args[1]) if len(args) > 1 else 10
        slugs = []
        for p in sorted(glob.glob(os.path.join(ROOT, "mezame", "*.txt"))):
            if is_source(p) and not os.path.exists(p.replace(".txt", ".polished.txt")):
                slugs.append(os.path.basename(p)[:-4])
        slugs = slugs[:n]
    else:
        slugs = args
    log("開始: %d本 (%s)" % (len(slugs), " ".join(slugs)))
    ok = ng = 0
    for s in slugs:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "polish.py"), "mezame/%s.txt" % s],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        last = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
        log(last)
        ok += r.returncode == 0
        ng += r.returncode != 0
    subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "compare.py"), "--all"], cwd=ROOT,
                   capture_output=True)
    log("完了: 通った %d本 / 差し戻し %d本。くらべファイルを作りました" % (ok, ng))


main()
