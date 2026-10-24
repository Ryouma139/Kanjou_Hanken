# テンプレート（HTML）一覧

`templates/` にある11個のHTMLの役割と中身のまとめです。
全体の仕組み（render、extends、include など）は [learning-notes.md](learning-notes.md) を参照してください。

---

## 全体の関係

```
base.html（外枠：全画面共通）
 ├─ hanken/record.html   記録する          ─include→ _phase.html ×2（観る前／観た後）
 ├─ hanken/after.html    観た後を記録       ─include→ _phase.html（観た後）
 ├─ hanken/reflect.html  ふり返り          ─include→ _stub.html → _half.html ×2
 ├─ hanken/mine.html     わたしの半券       ─include→ _stub.html → _half.html ×2（半券の数だけ）
 ├─ hanken/share.html    みんなの変化       ─include→ _stub.html → _half.html ×2（最大6枚）
 ├─ hanken/recent.html   最近の作品（ログイン直後に表示）
 ├─ hanken/calendar.html カレンダー         ─include→ _stub.html → _half.html ×2（選んだ日の分）
 ├─ registration/login.html   ログイン
 └─ registration/signup.html  ユーザー登録
```

| 種類 | ファイル | 特徴 |
|---|---|---|
| 外枠 | `base.html` | 他のすべてが `{% extends %}` で継承する |
| 画面 | `record` `after` `reflect` `mine` `share` `login` `signup` | view の `render()` で呼ばれる |
| 部品 | `_phase` `_stub` `_half`（`_` で始まる） | 画面から `{% include %}` で差し込まれる。単独では表示しない |

---

## 画面ごとの早見表

| テンプレート | URL | view | 受け取る主な値 | タブ |
|---|---|---|---|---|
| `hanken/record.html` | `/` | `record` | `form`（RecordForm） | 記録する |
| `hanken/after.html` | `/entry/<id>/after/` | `add_after` | `form`（AfterForm）、`entry` | 記録する |
| `hanken/reflect.html` | `/entry/<id>/reflect/` | `reflect` | `entry`、`care` | 記録する |
| `hanken/mine.html` | `/mine/` | `mine` | `entries` `open` `done` `stats` `comfort` `chart` `confirm` | わたしの半券 |
| `hanken/share.html` | `/share/?emo=...` | `share` | `total` `counts` `sel` `sel_name` `stats` `dist` `works` `recent` | みんなの変化 |
| `hanken/recent.html` | `/recent/` | `recent` | `sections` | 最近の作品 |
| `hanken/calendar.html` | `/calendar/?m=...&d=...` | `calendar` | `year` `month` `prev` `next` `weekdays` `cal` `picked` `day_entries` | カレンダー |
| `registration/login.html` | `/accounts/login/` | Django標準 `LoginView` | `form`、`next` | （なし） |
| `registration/signup.html` | `/accounts/signup/` | `signup` | `form`（SignupForm） | （なし） |

すべての画面テンプレートは、先頭で次の形をとります。
```html
{% extends "base.html" %}
{% load hanken_tags %}                                   ← 自作フィルタを使う画面だけ
{% block title %}○○｜感情の半券{% endblock %}            ← ブラウザのタブのタイトル
{% block content %} … {% endblock %}                     ← base.html の中身の場所に入る
```

---

## 外枠

### base.html
全画面共通の枠です。各画面は `{% block content %}` の中だけを書きます。

| 部分 | 内容 |
|---|---|
| `<head>` | 文字コード、スマホ対応（viewport）、Google Fonts、`style.css` |
| ヘッダー | 「Before / After of a story」、アプリ名（記録画面へのリンク）、説明文 |
| ユーザー欄 | ログイン中のみ：「○○ さん」と**ログアウトボタン**（POST で `logout` に送る） |
| タブ | ログイン中のみ：記録する／わたしの半券／みんなの変化／カレンダー／最近の作品。view から渡された `tab` と一致するタブに `aria-current="page"` を付けて強調。**管理者（`user.is_staff`）のときだけ**、最後に「管理画面」（`/admin/` へ移動）も出る |
| メッセージ | `messages.success(...)` で view が出した通知（「記録しました」など） |
| `<main>` | `{% block content %}`：**各画面の中身が入る場所** |
| ケアの文 | つらさが続くときの相談先（厚生労働省「まもろうよ こころ」へのリンク） |
| 広告 | `{% ads "footer" %}`：管理画面で「全ページの下」に登録した広告（相談窓口の文の下） |
| 最後 | `app.js` の読み込み |

ポイント：
- `{% block title %}感情の半券{% endblock %}` は既定のタイトル。各画面が上書きする
- `user` は settings.py の context_processors（`auth`）が自動で渡す。`{% if user.is_authenticated %}` でログイン前はタブを隠す
- ログアウトはリンクではなくフォーム（Django 5 からログアウトは POST のみ）

---

## 画面

### hanken/record.html（記録する）
作品と観る前の気持ちを記録する、最初の画面です。

```
<form method="post" enctype="multipart/form-data" novalidate>
 ├ 作品パネル       種類（本・映画など）のボタン、作品名
 ├ 観る前パネル     include _phase.html  ph=form.before_phase
 ├ チェック         「もう観終わった（観た後の気持ちも一緒に記録する）」 form.both
 ├ 観た後パネル     include _phase.html  ph=form.after_phase   ← id="after-panel"、最初は hidden
 ├ 共有パネル       名前つき／匿名／自分だけ
 └ 送信ボタン       id="submit-btn"
```

ポイント：
- **観た後パネルの表示切り替え**：`app.js` が `#id_both` のチェックを見て `#after-panel` の `hidden` を切り替える。ボタンの文字も `data-label-one`「観る前を記録する」／`data-label-both`「前と後を記録する」で入れ替わる
- JavaScript がなくても、エラーで再表示されたときに `{% if form.both.value %}` で正しい状態になる
- `{{ form.non_field_errors }}`：項目に属さないエラー（`clean()` の中のチェックなど）を表示する
- 共有の説明に「写真やひとことも表示されます」と書いてある
- 送信後：「もう観終わった」なら `reflect` へ、そうでなければこの画面に戻ってメッセージを表示

### hanken/after.html（観た後を記録）
「鑑賞中」の半券に、観た後の気持ちを書き足す画面です。

```
<form method="post" enctype="multipart/form-data" novalidate>
 ├ 観る前のふり返り  種類、作品名、観る前の気持ち（色つき）・気分・日付
 ├ 観た後パネル      include _phase.html  ph=form.after_phase
 └ ボタン            「観た後を記録する」／「やめる」（わたしの半券へ）
```

ポイント：
- `entry` は view が `get_object_or_404(Entry, pk=pk, user=request.user)` で取った**自分の**半券
- `enctype="multipart/form-data"` がないと写真が届かない
- `{% csrf_token %}` がないと 403 エラーになる
- `novalidate` でブラウザのチェックを止め、Django 側のチェックと日本語のエラーを使う
- 記録済みの半券で開くと、前の値が入った状態になる（書き直しができる）
- 送信後：`reflect` へ

### hanken/reflect.html（ふり返り）
観た後を記録した直後に出る、気持ちの変化の画面です。

| 部分 | 内容 |
|---|---|
| 見出し | 『作品名』を観て |
| 気持ちの変化 | 観る前の気持ち → 観た後の気持ち（それぞれ色の丸つき） |
| 気分の変化 | `before_mood → after_mood` と `{{ entry.delta\|signed }}`（`+3` など）。`trend` で上がったら・下がったら色が変わる |
| ケアのひとこと | `{{ care }}`：view が `analysis.care_line(entry.delta)` で作った文 |
| ボタン | 続けて記録する／わたしの半券を見る／**同じ気持ちだった人を見る**（`/share/?emo=観る前の気持ち`） |
| 半券 | `include _stub.html with e=entry own=True`（共有・削除のボタンは出さない） |

ポイント：
- 観た後が未記録の半券でこのURLを開くと、view が `after` へ移動させる

### hanken/mine.html（わたしの半券）
自分の半券の一覧と、気分の分析です。

```
半券が0枚 → 空の案内（「最初の半券をつくる」ボタン）
半券がある →
 ├（見終わった半券があるとき）
 │  ├ 数字3つ     半券の数／気分の平均変化／気分が上がった割合
 │  ├ 気分の動き  SVG のグラフ（観る前→観た後を線で結ぶ。最近の数件）
 │  └ 心のお守り作品  気分が上がった作品のランキング
 ├ 鑑賞中        include _stub.html（own=True manage=True）
 └ 見終わった半券  include _stub.html（own=True manage=True）
```

| 値 | 作っている場所 |
|---|---|
| `entries` / `open` / `done` | `views.mine()`。`is_done` で鑑賞中と見終わったものに分ける |
| `stats` | `analysis.summarize(done)` |
| `comfort` | `analysis.comfort_works(done)` |
| `chart` | `analysis.slope_chart(done)`。線の座標・目盛りまで Python 側で計算済み |
| `confirm` | URL の `?confirm=半券のid`（削除の確認表示に使う） |

ポイント：
- グラフはライブラリを使わず、`<svg>` の `<line>` と `<circle>` を `{% for %}` で並べて描いている。点の色は気持ちの色（`var(--e-...)`）、線の色は `slope up/down` のクラスで決まる
- `<title>` を入れているので、線にマウスを乗せると「作品名：5→8」と出る
- `{{ stats.avg|signed:1 }}`：小数点以下1桁で `+1.5` のように表示
- `{{ forloop.counter }}`：`{% for %}` の何回目か（ランキングの順位）
- `manage=True` を渡しているので、半券に共有の変更と削除のボタンが出る

### hanken/share.html（みんなの変化）
共有された半券を、**観る前の気持ち別**に集計する画面です。

```
共有された半券が0枚 → 空の案内
ある →
 ├ 気持ちの選択   観る前の気持ちのチップ（件数つき）。押すと ?emo=キー で再表示
 ├ 見出し        〈不安〉で観始めた人は、観たあと…
 ├ 数字3つ       半券の数／気分の平均変化／気分が上がった人の割合
 ├ 観た後の気持ち  横棒グラフ（分布）
 ├ 気持ちが動いた作品  作品ランキング（何人の平均か）
 └ 最近の半券     include _stub.html（own=False）最大6枚
```

| 値 | 作っている場所 |
|---|---|
| `total` | 共有された半券（`private` 以外・観た後まで記録済み）の数 |
| `counts` | `analysis.before_counts(pool)`：観る前の気持ちごとの件数 |
| `sel` / `sel_name` | 選んでいる気持ち。`?emo=` がなければ、自分の最新の半券の気持ち、なければ一番多い気持ち |
| `stats` | `analysis.summarize(group)` |
| `dist` | `analysis.after_distribution(group)` |
| `works` | `analysis.work_ranking(group)` |
| `recent` | 選んだ気持ちの半券を新しい順に6枚。`author` に表示名を入れてある |

ポイント：
- 選択中のチップは `class="chip on"` と `aria-current="true"` で強調
- 横棒の長さは `style="width:{{ d.pct|floatformat:0 }}%"`（割合を整数にして CSS の幅に使う）
- `own=False` なので、半券の下には投稿者名（「匿名さん」など）だけが出る

### hanken/recent.html（最近の作品）
ログイン・登録の直後に出る画面です。管理画面で登録した作品を、**映画・本・ドラマごとに更新日時の新しい順で10件ずつ**並べます。

```
 ├ 見出し        最近の作品、「記録をはじめる」ボタン（記録する画面へ）
 ├ 映画          カードが横に10枚並ぶ（はみ出したら横スクロール）
 │                 カード：画像（縦長 2:3）＋左上に順位、作品名（リンクがあれば ↗）、ひとこと紹介、更新日
 ├ 本            同じ
 └ ドラマ        同じ（0件なら「まだ登録されていません」。管理者には追加リンク）
```

ポイント：
- 時間で別の画面へ移動することはない。ゆっくり一覧を見てから「記録をはじめる」かタブで移動する
- リンクがある作品は**カード全体**が `<a>`、ない作品は `<div>`（`{% if w.url %}<a …>{% else %}<div …>{% endif %}` で開始と終了のタグを切り替える）
- 画像は `<img src="{{ w.cover_url }}">`。`cover_url` はアップロードした画像を優先し、なければ画像URL（models.py のプロパティ）
- `referrerpolicy="no-referrer"`：ほかのサイトの画像を読み込むとき、どのページから来たかを相手に伝えない。伝えると表示を断るサイトもあるため
- 画像がない（または読み込めない）作品は、種類ごとの色のタイルに「映画」「本」「ドラマ」の文字（色は style.css の `.cover.kind-movie` など）
- 画像は `object-fit:cover` で 2:3 の枠に合わせて切り取る。作品名と紹介は2行を超えると「…」で省略
- 作品の追加リンク `{% url 'admin:hanken_work_add' %}` は、管理画面の「作品を追加」ページの名前
- 作品のリンクは `target="_blank"` で別のタブに開く。`rel="noopener noreferrer"` は、開いた先のページからこの画面を操作されないようにするための安全策

### hanken/calendar.html（カレンダー）
自分の半券を、月のカレンダーで数える画面です。**観る前と観た後がそろった半券を1枚**として、観終わった日（観た後を記録した日）に数えます。鑑賞中の半券は数えません。

```
 ├ 月の切り替え   ‹ 2026年10月 ›（?m=2026-09 などで前後の月へ）
 ├ カレンダー     日曜はじまりの表。半券がある日は色がつき、枚数が出る
 ├ 下の行         数え方の説明、「今月へ」（今月以外を見ているとき）
 ├ 数字3つ        この月の半券／記録した日／選んだ日の半券
 └ 選んだ日の半券  include _stub.html（own=True）
```

ポイント：
- `cal` は `analysis.month_calendar()` が作る。`cal.weeks` は「週のリスト」で、1週は7日分のマス（`day` `in_month` `n` `today`）
- 半券がある日だけ `<a>` にして、`?m=2026-10&d=17#day` へのリンクにする。`#day` で、選んだ日の見出しまで画面が移動する
- 今日は日付に下線、選んだ日は枠線、前後の月の日付は薄く表示
- `{% for %}…{% empty %}…{% endfor %}`：リストが空のときの表示を書ける

### registration/login.html（ログイン）
Django 標準の `LoginView` が、この決まった名前のファイルを使います。

ポイント：
- 入力欄の名前は「ニックネーム」だが、中身は Django の `username`
- エラー時は「ニックネームかパスワードが違います」とだけ出す（どちらが違うかは教えない）
- `<input type="hidden" name="next" value="{{ next }}">`：ログイン後に元のページ（`?next=`）へ戻るため
- 「はじめての方はこちら」で `signup` へ

### registration/signup.html（ユーザー登録）
`views.signup()` が使う、登録画面です。

ポイント：
- 入力欄を1つずつ書かず、`{% for f in form %}` でフォームの全項目を順に出している。項目を増やしてもテンプレートの変更が不要
- `{{ f.help_text|safe }}`：パスワードの条件など、Django が用意した説明文。HTML を含むので `safe` で表示する
- ニックネームは「名前つきで共有」した半券に出るので、本名でなくてよいと案内している
- 登録すると、そのままログインして記録画面へ

---

## 部品

### hanken/_phase.html（入力欄：観る前／観た後）
使う場所：`record.html`（2回）、`after.html`（1回）

受け取る値：`ph`（forms.py の `before_phase` / `after_phase` が返す辞書）

| `ph` の中身 | 例（観た後） |
|---|---|
| `ph.title` / `ph.eyebrow` | 「観た後の気持ち」／「After」 |
| `ph.emo` | `form["after_emo"]` |
| `ph.mood` | `form["after_mood"]` |
| `ph.photo` | `form["after_photo"]` |
| `ph.note` | `form["after_note"]` |

作るもの：
1. **気持ちの選択**：`{% for radio in ph.emo %}` でラジオボタンを1つずつ出し、色つきのチップにする（`--c:var(--e-{{ radio.data.value }})`）
2. **気分のスライダー**：1〜10。`data-mood-out` / `data-mood-word` を `app.js` が見て「7 / 10」「いい感じ」を更新する。初期表示は `mood_word` フィルタで作る
3. **写真**：選ぶボタンと、`data-preview-for` のプレビュー枠（`app.js` が選んだ画像を表示）
4. **ひとこと**：テキストエリア
5. 各項目のエラー：`{{ ph.emo.errors }}` など

ポイント：
- 項目名（`before_` / `after_`）をテンプレートに書かず、`ph` で受け取るので、**同じ部品で観る前と観た後の両方を作れる**

### hanken/_stub.html（半券1枚）
使う場所：`reflect.html`、`mine.html`、`share.html`

受け取る値：

| 値 | 意味 |
|---|---|
| `e` | 半券（Entry）。`{% for e in ... %}` の変数、または `with e=entry` |
| `own` | 自分の半券として表示するか |
| `manage` | 共有の変更・削除のボタンを出すか |
| `confirm` | 削除の確認中の半券の id（mine.html から） |

構造：
```
<article class="stub" id="e{{ e.pk }}">     ← id はページ内リンク（#e12）用
 ├ 頭     （作品に結びついていれば）作品の小さな画像、種類、作品名（作品にリンクがあればリンク ↗）、作成日
 ├ 左     include _half.html  lbl="BEFORE"  before_ の項目
 ├ 中央   切り取り線：変化量（+3 など）。未記録なら「鑑賞中」
 ├ 右     include _half.html  lbl="AFTER"   after_ の項目
 └ 足
    own=True
      見終わった → 共有の状態（「共有中」など）／鑑賞中 → 「観た後を記録する」ボタン
      manage=True → 共有のセレクト（選ぶと app.js が即送信）、削除
    own=False → 投稿者名（「匿名さん」など）
```

ポイント：
- **作品との結びつき**：`e.work` は半券に結びついた作品（なければ空）。`{% if e.work.cover_url %}` のように、`e.work` が空でもエラーにならず「なし」として扱われる
- **削除は2段階**：「削除」リンクで `?confirm=id` 付きで開き直す → 「この半券を削除しますか？」と「削除する」ボタンが出る → POST で削除。JavaScript を使わずに確認を出している
- `e.pk|stringformat:"d"`：数値の id を文字列にして、URL から来た `confirm`（文字列）と比べる
- `<noscript>`：JavaScript が無効なときだけ「変更」ボタンを出す
- 削除・共有の変更は `{% csrf_token %}` 付きの POST（`@require_POST` の view）

### hanken/_ads.html（広告）
使う場所：`{% ads "場所" %}` タグ（base.html の下、reflect.html、recent.html）

受け取る値：`ads`（その場所の表示中の広告のリスト）

```
<aside class="ads" aria-label="広告">
  ├ PR の札 ＋ 広告タグ（1件目）
  └ PR の札 ＋ 広告タグ（2件目）…
```

ポイント：
- **`{{ ad.html|safe }}`**：Django は `{{ }}` の中の `<` などを自動で `&lt;` に変える（スクリプトを埋め込まれないため）。`|safe` はそれを止めて、HTML をそのまま出す指示。**管理者だけが入力できる欄なので使ってよい**。一般のユーザーが入力する値には絶対に使わない
- 「PR」の札はテンプレート側で必ず付けるので、広告タグに書き忘れても表示される（ステルスマーケティング規制への対応）
- 広告が0件なら、枠ごと何も出さない

### hanken/_half.html（半券の片側）
使う場所：`_stub.html`（BEFORE と AFTER の2回）

受け取る値：`lbl`（"BEFORE" / "AFTER"）、`emo`、`mood`、`note`、`photo`

```
気持ちあり
 ├ 写真あり → <img src="{{ photo.url }}">（media/ の写真）
 │  写真なし → 気持ちの色のグラデーションと、気持ちの1文字（emo_char）
 ├ 気持ちのタグ（色の丸＋名前）と、気分「7/10」
 └ ひとこと（あれば）
気持ちなし（AFTER が未記録）→ 点線の枠に「まだ」
```

ポイント：
- **`media/` に保存した写真を表示しているのは、ここの `<img>` だけ**
- `loading="lazy"`：画面に近づいたときに画像を読み込む（一覧を速く表示するため）
- 写真が読み込めないと、`app.js` が `<img>` を消して気持ちの色の表示に切り替える
- 色は `style="--c:var(--e-{{ emo }})"` で CSS 変数に入れ、`style.css` 側で使う

---

## よく出てくる書き方

| 書き方 | 意味 | 例 |
|---|---|---|
| `{{ 値 }}` | 値を表示（HTML は自動でエスケープ） | `{{ entry.title }}` |
| `{{ 値\|フィルタ }}` | 変換して表示 | `{{ e.kind\|kind_name }}`、`{{ e.created_at\|date:"Y.n.j" }}` |
| `{% if %}` | 条件 | `{% if user.is_authenticated %}` |
| `{% for %}` | 繰り返し | `{% for e in done %}`、`{{ forloop.counter }}` |
| `{% url '名前' 引数 %}` | URL を作る | `{% url 'hanken:after' e.pk %}` |
| `{% static 'パス' %}` | static ファイルの URL | `{% static 'hanken/app.js' %}` |
| `{% csrf_token %}` | POST フォームの合言葉 | すべての POST フォーム |
| `{% include "部品" with x=... %}` | 部品に値を渡して差し込む | `{% include "hanken/_stub.html" with own=True %}` |
| `style="--c:var(--e-{{ emo }})"` | 気持ちの色を CSS 変数で渡す | チップ、タグ、グラフの点 |
| `data-○○="..."` | `app.js` が要素を見つけるための目印 | `data-mood-out`、`data-autosubmit` |

自作フィルタ（[hanken/templatetags/hanken_tags.py](../hanken/templatetags/hanken_tags.py)）：

| フィルタ | 結果 |
|---|---|
| `emo_name` | 気持ちのキー → 名前（anxious → 不安） |
| `emo_char` | 気持ちのキー → 1文字 |
| `kind_name` | 作品の種類のキー → 名前 |
| `mood_word` | 気分の数値 → 言葉（7 → いい感じ） |
| `signed` | 数値 → `+4` / `−2` / `±0`。`signed:1` で小数1桁 |
| `trend` | 数値 → `up` / `down` / `flat`（CSS のクラス名に使う） |
