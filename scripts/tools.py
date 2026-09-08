# -*- coding: utf-8 -*-
"""ツールのページを作る。

    python scripts/tools.py

いまあるもの:
  tools/moon-sign.html   月星座を調べる

計算はすべて訪問者のブラウザの中で行う。入力された生年月日は
どこにも送信しない。ライブラリ（astronomy-engine, MIT）は
tools/lib/ に同梱してあり、外部のCDNには接続しない。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

_src = io.open(os.path.join(HERE, "build.py"), encoding="utf-8").read()
_src = _src.replace('if __name__ == "__main__":', 'if False:')
_ns = {"__file__": os.path.join(HERE, "build.py"), "__name__": "borrowed"}
exec(compile(_src, "build.py", "exec"), _ns)
page = _ns["page"]
SITE = _ns["SITE"]


MOON = """
<main class="wrap">
<article class="entry">
  <p class="crumb">TOOL</p>
  <h1>月星座を調べる</h1>

  <p class="lead">生まれたときに月がどの星座にあったかを計算します。
  月は空を速く動くので、<b>日付だけでなく時刻が要ります。</b></p>

  <div class="note">
    <b>入力した内容は、このページの中だけで計算されます。</b>
    サーバーにも第三者にも送信されません。保存もされないので、ページを閉じると消えます。
    登録もメールアドレスも必要ありません。
  </div>

  <form id="f" class="toolform" autocomplete="off">
    <div class="row">
      <label>生まれた年
        <input type="number" id="y" min="1800" max="2100" placeholder="1990" required>
      </label>
      <label>月
        <input type="number" id="mo" min="1" max="12" placeholder="7" required>
      </label>
      <label>日
        <input type="number" id="d" min="1" max="31" placeholder="15" required>
      </label>
    </div>
    <div class="row">
      <label>時
        <input type="number" id="h" min="0" max="23" placeholder="14">
      </label>
      <label>分
        <input type="number" id="mi" min="0" max="59" placeholder="30">
      </label>
      <label class="chk">
        <input type="checkbox" id="unknown"> 時刻がわからない
      </label>
    </div>
    <p class="hint">日本で生まれた方は、そのまま日本時間で入力してください。
    海外で生まれた方は、その土地の時刻ではなく<b>日本時間に直した時刻</b>を入れてください
    （いまは日本時間のみに対応しています）。</p>
    <button type="submit">調べる</button>
  </form>

  <div id="out" hidden></div>

  <h2>この計算について</h2>
  <ul>
    <li><b>方式</b> — 西洋占星術で一般的な<b>トロピカル方式</b>（春分点を牡羊座0度とする）で出しています。
      実際の星の位置を使う<b>サイデリアル方式</b>とは、2026年時点でおよそ24度ずれます。
      詳しくは <a href="../moon-sign.html">月星座</a> をご覧ください。</li>
    <li><b>位置</b> — 地球の中心から見た月の黄経（見かけの位置）を使っています。
      月星座を出すだけなら出生地は影響しません。影響するのはアセンダントとハウスです。</li>
    <li><b>計算</b> — <a href="https://github.com/cosinekitty/astronomy" target="_blank" rel="noopener">astronomy-engine</a>
      （MITライセンス）を使っています。ファイルはこのサイトに同梱してあり、
      外部のサーバーには接続しません。</li>
    <li><b>境目のとき</b> — 星座の変わり目の前後30分ほどに当たる場合は、
      出生時刻の記録そのものに誤差があることが多いので、両方を表示します。</li>
  </ul>

  <h2>もっと知る</h2>
  <p><a href="../moon-sign.html">月星座とは何か</a>（来歴、太陽星座との違い、方式のずれについて）</p>

</article>
</main>

<script src="lib/astronomy.browser.min.js"></script>
<script>
(function () {
  var SIGNS = ["牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座",
               "天秤座","蠍座","射手座","山羊座","水瓶座","魚座"];
  var SIGNS_EN = ["Aries","Taurus","Gemini","Cancer","Leo","Virgo",
                  "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"];

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;"}[c];
    });
  }

  // 日本時間 -> UTC の Date
  function jst(y, mo, d, h, mi) {
    return new Date(Date.UTC(y, mo - 1, d, h - 9, mi, 0));
  }

  function moonLon(dt) {
    var s = Astronomy.EclipticGeoMoon(dt);
    var lon = s.lon % 360;
    if (lon < 0) { lon += 360; }
    return lon;
  }

  function sunLon(dt) {
    var s = Astronomy.SunPosition(dt);
    var lon = s.elon % 360;
    if (lon < 0) { lon += 360; }
    return lon;
  }

  function sign(lon) { return Math.floor(lon / 30) % 12; }
  function degIn(lon) { return lon - Math.floor(lon / 30) * 30; }

  function fmt(lon) {
    var i = sign(lon), dg = degIn(lon);
    var deg = Math.floor(dg);
    var min = Math.round((dg - deg) * 60);
    if (min === 60) { min = 0; deg += 1; }
    // 29度59.7分などを丸めて30度になった場合は、次の星座の0度に送る
    if (deg >= 30) { deg = 0; i = (i + 1) % 12; }
    return {name: SIGNS[i], en: SIGNS_EN[i], deg: deg, min: min, idx: i};
  }

  // 1948-1951 の日本の夏時間の期間にかかるか（正確な境界は年ごとに違うため注意喚起のみ）
  function maybeDst(y, mo) {
    return (y >= 1948 && y <= 1951) && (mo >= 4 && mo <= 9);
  }

  document.getElementById("unknown").addEventListener("change", function () {
    var on = this.checked;
    document.getElementById("h").disabled = on;
    document.getElementById("mi").disabled = on;
  });

  document.getElementById("f").addEventListener("submit", function (ev) {
    ev.preventDefault();
    var out = document.getElementById("out");
    var y = parseInt(document.getElementById("y").value, 10);
    var mo = parseInt(document.getElementById("mo").value, 10);
    var d = parseInt(document.getElementById("d").value, 10);
    var unknown = document.getElementById("unknown").checked;
    var h = parseInt(document.getElementById("h").value, 10);
    var mi = parseInt(document.getElementById("mi").value, 10);
    if (isNaN(h)) { h = 12; }
    if (isNaN(mi)) { mi = 0; }

    if (isNaN(y) || isNaN(mo) || isNaN(d)) {
      out.hidden = false;
      out.innerHTML = '<div class="note">生まれた年・月・日を入れてください。</div>';
      return;
    }
    var chk = jst(y, mo, d, 12, 0);
    if (chk.getUTCFullYear() !== y || (chk.getUTCMonth() + 1) !== mo) {
      out.hidden = false;
      out.innerHTML = '<div class="note">その日付は存在しないようです。もう一度ご確認ください。</div>';
      return;
    }

    var html = "";

    if (unknown) {
      var a = moonLon(jst(y, mo, d, 0, 0));
      var b = moonLon(jst(y, mo, d, 23, 59));
      var fa = fmt(a), fb = fmt(b);
      if (fa.idx === fb.idx) {
        html += '<h2 class="resulth">月星座は <span class="big">' + esc(fa.name) + '</span></h2>';
        html += '<p>この日は一日じゅう月が' + esc(fa.name) +
                'にあったので、<b>時刻が分からなくても決まります。</b></p>';
      } else {
        html += '<h2 class="resulth">月星座は <span class="big">' + esc(fa.name) +
                '</span> か <span class="big">' + esc(fb.name) + '</span></h2>';
        html += '<p>この日は途中で月の星座が変わっています。' +
                '<b>時刻が分からないと、どちらかまでしか絞れません。</b>' +
                '朝生まれなら' + esc(fa.name) + '、夜生まれなら' + esc(fb.name) +
                'に近くなります。</p>';
      }
      html += '<p class="hint">母子手帳に出生時刻が書かれていることがあります。' +
              '分かれば、上の「時刻がわからない」のチェックを外して入れ直してください。</p>';
    } else {
      var dt = jst(y, mo, d, h, mi);
      var ml = moonLon(dt), sl = sunLon(dt);
      var fm = fmt(ml), fs = fmt(sl);
      html += '<h2 class="resulth">月星座は <span class="big">' + esc(fm.name) + '</span></h2>';
      html += '<table class="kv result"><tr><th>月星座</th><td><b>' + esc(fm.name) + '</b>（' +
              esc(fm.en) + '）　' + fm.deg + '度' + fm.min + '分</td></tr>' +
              '<tr><th>太陽星座</th><td>' + esc(fs.name) + '（' + esc(fs.en) + '）　' +
              fs.deg + '度' + fs.min + '分</td></tr></table>';

      // 境目の判定：前後30分で星座が変わるか
      var before = fmt(moonLon(new Date(dt.getTime() - 30 * 60000)));
      var after = fmt(moonLon(new Date(dt.getTime() + 30 * 60000)));
      if (before.idx !== fm.idx || after.idx !== fm.idx) {
        var other = (before.idx !== fm.idx) ? before.name : after.name;
        html += '<div class="note"><b>星座の変わり目のすぐ近くです。</b>' +
                '前後30分で' + esc(other) + 'になります。' +
                '出生時刻の記録は数十分ずれていることがあるため、' +
                '<b>両方を見ておくことをおすすめします。</b></div>';
      }
    }

    if (maybeDst(y, mo)) {
      html += '<div class="note"><b>この時期の日本には夏時間がありました。</b>' +
              '1948年から1951年の夏のあいだ、時計が1時間進められていました。' +
              'その期間に生まれた場合、結果が1時間ぶんずれている可能性があります。</div>';
    }

    html += '<p class="hint">この計算はトロピカル方式（西洋占星術で一般的な方式）です。' +
            '実際の星の位置を使う方式では、星座が1つずれることがあります。' +
            '<a href="../moon-sign.html">くわしく</a></p>';
    html += '<p class="hint">入力した内容はどこにも送信されていません。' +
            'ページを閉じると消えます。</p>';

    out.hidden = false;
    out.innerHTML = html;
    out.scrollIntoView({behavior: "smooth", block: "start"});
  });
})();
</script>
"""


def write(name, text):
    full = os.path.join(ROOT, name)
    d = os.path.dirname(full)
    if d:
        os.makedirs(d, exist_ok=True)
    io.open(full, "w", encoding="utf-8", newline="\n").write(text)


write("tools/moon-sign.html", page(
    "月星座を調べる — めざめ",
    "生年月日と時刻から月星座を計算します。入力はブラウザの中だけで処理され、"
    "どこにも送信されません。登録もメールアドレスも不要です。",
    SITE + "/tools/moon-sign.html", MOON, current="", ogtype="website", sec="tools"))

print("ツールのページを生成しました（tools/moon-sign.html）")
