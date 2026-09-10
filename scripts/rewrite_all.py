# -*- coding: utf-8 -*-
"""めざめ＋スパイラルの全記事を Terra で書き直し、検査に通ったものだけ元ファイルを置き換える。

    python scripts/rewrite_all.py

・元の記事は先に「元の記事バックアップ/」に写しておくこと（このスクリプトは写さない）
・1本ごとに polish.py --apply を呼ぶ（検査に落ちたら polish.py 側で1回やり直し。それでも落ちたら元のまま）
・進み具合は _書き直しログ.txt に書く。すでに置き換え済み（ログに [置き換え] がある）の記事は飛ばす
"""
import glob
import io
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "_書き直しログ.txt")
NL = chr(10)


def log(msg):
    line = time.strftime("%H:%M ") + msg
    print(line)
    io.open(LOG, "a", encoding="utf-8", newline=NL).write(line + NL)


def targets():
    out = []
    for d in ("mezame", "spiral"):
        for p in sorted(glob.glob(os.path.join(ROOT, d, "*.txt"))):
            b = os.path.basename(p)
            if any(x in b for x in (".draft.", ".polished.", ".rejected.", ".gpt.")):
                continue
            out.append(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    return out


def already_done():
    if not os.path.exists(LOG):
        return set()
    done = set()
    for line in io.open(LOG, encoding="utf-8"):
        if "[置き換え]" in line or "[元のまま]" in line:
            done.add(line.split("]", 1)[1].strip().split()[0])
    return done


def main():
    files = targets()
    done = already_done()
    todo = [f for f in files if os.path.basename(f) not in done]
    log("開始: 全%d本のうち残り%d本" % (len(files), len(todo)))
    ok = ng = 0
    for f in todo:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "polish.py"), f, "--apply"],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        lines = [l for l in r.stdout.strip().splitlines() if l.strip()]
        if r.returncode == 0:
            ok += 1
            log(lines[-1] if lines else "[置き換え] " + os.path.basename(f))
        else:
            ng += 1
            reason = " / ".join(l.strip(" -") for l in lines if l.startswith("   -")) or (r.stderr.strip()[-200:])
            log("[元のまま] %s  3回とも検査に落ちた: %s" % (os.path.basename(f), reason))
        # 途中でできた差し戻しファイルは残さない（build.py は読まないが、散らかるので）
        rej = os.path.join(ROOT, f.replace(".txt", ".rejected.txt"))
        if os.path.exists(rej):
            os.remove(rej)
    log("完了: 置き換え %d本 / 元のまま %d本" % (ok, ng))


main()
