# -*- coding: utf-8 -*-
"""固定ページ（このサイトについて／プライバシーポリシー）を作る。

build.py と同じ体裁で出力する。内容を変えるときはこのファイルを直す。
    python scripts/static.py
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://ohashinatsuki.github.io/occult-taizen"

# build.py のテンプレートを読み込んで使う
src = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "build.py"),
              encoding="utf-8").read()
ns = {}
head = src.split('HEAD = """')[1].split('"""')[0]
foot = src.split('FOOT = """')[1].split('"""')[0]


def page(title, desc, canon, body, current=""):
    cur = {k: (' aria-current="page"' if k == current else "")
           for k in ["top", "aiueo", "kuni", "bunya", "about"]}
    h = head.format(title=title, desc=desc, canon=canon, ogtitle=title,
                    ogtype="website", ogimage="", base="",
                    c_top=cur["top"], c_aiueo=cur["aiueo"], c_kuni=cur["kuni"],
                    c_bunya=cur["bunya"], c_about=cur["about"])
    return h + body + foot.format(base="")


ABOUT = """
<main class="wrap">
<article class="entry">
  <h1>このサイトについて</h1>

  <p class="lead">世界オカルト大全は、世界じゅうの怪異、未確認生物、古代の謎、消えた文明、都市伝説を集めた事典です。面白い話として楽しめるように書きますが、<b>嘘は書きません。</b></p>

  <h2>書き方の約束</h2>
  <p>オカルトを扱うサイトでいちばん大事なのは、<b>「確認されていること」と「そう言われていること」を混ぜない</b>ことだと考えています。このサイトでは、次のように書き分けます。</p>
  <ul>
    <li><b>本文</b> — 何が起きたと語られているか、どう広まったかを書きます。</li>
    <li><b class="ok">確認されていること</b>と見出しの付いた枠 — 調査や公的な発表で裏付けが取れている事実だけを入れます。「作り物だと判明した」「年代測定の結果」など、話に不都合な事実もここに書きます。</li>
    <li><b>語られてきた説</b> — 有力とされる説明を並べます。断定はしません。</li>
  </ul>
  <p>怪異の魅力は、それが本当かどうか分からないところにあります。<b>分からないものを「分かった」と書くと、その魅力は消えます。</b>だから、分からないことは分からないままにしておきます。</p>

  <h2>載せないもの</h2>
  <ul>
    <li><b>実在の民族・宗教・団体を敵に仕立てる陰謀論。</b>特定の集団への攻撃になる主張は扱いません。</li>
    <li><b>健康や医療に関する根拠のない主張。</b>「これで病気が治る」という類の話は載せません。人の命に関わるためです。</li>
    <li><b>遺体、事故現場、グロテスクな画像。</b>亡くなった方と遺族の尊厳のためです。</li>
    <li><b>実在の事件の被害者を晒す心霊スポット紹介。</b>実際に人が亡くなった場所を、興味本位の見世物にはしません。</li>
  </ul>

  <h2>画像について</h2>
  <p>掲載している画像は、次のいずれかです。</p>
  <ul>
    <li><b>著作権の切れた古い図版・写真</b>（19世紀の版画、古い新聞挿絵など）。出典と権利表示を画像の下に必ず書きます。</li>
    <li><b>AIで生成したイメージ図。</b>この場合は「AI生成のイメージ図」と明記します。</li>
  </ul>
  <p><b>AIで作った画像を「本物の写真」として出すことは、絶対にしません。</b>偽の証拠を本物として見せることは、このサイトがやってはいけないことだと考えています。</p>

  <h2>索引の使い方</h2>
  <ul>
    <li><a href="aiueo.html">五十音索引</a> — 名前が分かっているとき。辞書と同じ引き方です。</li>
    <li><a href="kuni.html">国別索引</a> — 国や地域から探すとき。</li>
    <li><a href="bunya.html">分野別索引</a> — 未確認生物、UFO、古代の謎など、種類から探すとき。</li>
  </ul>

  <h2>更新について</h2>
  <p>事典の項目は随時追加しています。あわせて、週に一度、世界のオカルト関連の出来事を確認して記録しています。</p>

  <h2>運営者</h2>
  <p>柏木 亮（かしわぎ りょう）／日本・岐阜県</p>

  <h2>訂正について</h2>
  <p>誤りを見つけた場合は訂正します。とくに「確認されていること」の枠に書いた内容に誤りがあった場合は、速やかに直します。</p>

  <h2>免責</h2>
  <p>掲載内容は、公開された資料や報道にもとづいて作成していますが、その正確性・完全性を保証するものではありません。当サイトの情報を利用したことによって生じた損害について、運営者は責任を負いません。外部サイトへのリンク先の内容についても責任を負いません。</p>

  <div class="rev"></div>
</article>
</main>
"""

PRIVACY = """
<main class="wrap">
<article class="entry">
  <h1>プライバシーポリシー</h1>

  <p class="lead">世界オカルト大全（以下「当サイト」）における、利用者の情報の取り扱いについて説明します。</p>

  <h2>当サイトが自ら集めない情報</h2>
  <p>当サイトには、会員登録、ログイン、コメント欄、購入手続きがありません。氏名、メールアドレス、住所、電話番号、決済情報などを、運営者が入力してもらって集めることはありません。</p>

  <h2>アクセスにともなって記録される情報</h2>
  <p>当サイトは GitHub Pages（GitHub, Inc.）で公開されています。ページを表示する際、技術的な仕組みとして、同社のサーバーに IP アドレスやブラウザの種類などのアクセス情報が記録されることがあります。取り扱いは <a href="https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener">GitHub プライバシーステートメント</a> に従います。</p>
  <p>画面表示のために Google Fonts（Google LLC）からフォントを読み込んでいます。この際にも、同社に IP アドレス等の技術情報が送信されます。取り扱いは <a href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">Google プライバシーポリシー</a> に従います。</p>

  <h2>広告配信について</h2>
  <p>当サイトでは、運営費をまかなうため、第三者配信の広告サービス「Google AdSense」の導入を予定しています。導入後は、以下のとおりとなります。</p>
  <ul>
    <li>Google を含む第三者配信事業者は、Cookie を使用して、利用者が過去に当サイトや他のサイトへアクセスした情報に基づいて広告を表示することがあります。</li>
    <li>利用者は <a href="https://adssettings.google.com/authenticated?hl=ja" target="_blank" rel="noopener">広告設定</a> でパーソナライズ広告を無効にできます。また <a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener">www.aboutads.info</a> では、第三者配信事業者の Cookie を個別に無効にできます。</li>
    <li>詳細は <a href="https://policies.google.com/technologies/ads?hl=ja" target="_blank" rel="noopener">広告 – ポリシーと規約 – Google</a> をご確認ください。</li>
  </ul>
  <div class="note">広告が実際に表示されるようになるまで、当サイトから広告 Cookie が設定されることはありません。</div>

  <h2>アクセス解析について</h2>
  <p>現在、当サイトはアクセス解析ツールを導入していません。導入する場合は、このページを更新したうえで行います。</p>

  <h2>Cookie の拒否について</h2>
  <p>利用者はブラウザの設定により Cookie の保存を拒否できます。当サイトの閲覧そのものは、Cookie を拒否した状態でも問題なく行えます。</p>

  <h2>免責事項</h2>
  <p>当サイトの掲載内容は、公開された資料や報道にもとづいて作成していますが、その正確性・完全性を保証するものではありません。当サイトの情報を利用したことによって生じた損害について、運営者は責任を負いません。当サイトからリンクした外部サイトの内容および個人情報の取り扱いについても、責任を負いません。</p>

  <h2>著作権</h2>
  <p>当サイトが独自に作成した文章および構成についての権利は運営者に帰属します。引用元となる資料の権利は、それぞれの権利者に帰属します。掲載画像の権利表示は、各画像の下に記載しています。</p>

  <h2>ポリシーの変更</h2>
  <p>本ポリシーは、法令の改正やサービスの追加にともない、予告なく変更することがあります。変更後の内容は、このページに掲載した時点から適用されます。</p>

  <div class="rev"></div>
</article>
</main>
"""


def write(name, text):
    io.open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="\n").write(text)


write("about.html", page("このサイトについて — 世界オカルト大全",
                         "世界オカルト大全の編集方針。確認されている事実と語り伝えられている話をどう書き分けているか、何を載せないか、画像の扱いについて。",
                         SITE + "/about.html", ABOUT, current="about"))
write("privacy.html", page("プライバシーポリシー — 世界オカルト大全",
                           "世界オカルト大全のプライバシーポリシー。Cookie、広告配信、アクセス情報の取り扱いについて。",
                           SITE + "/privacy.html", PRIVACY))
print("固定ページ 2枚を生成しました")
