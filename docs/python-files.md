# Python ファイル一覧（機能まとめ）

このプロジェクトの `.py` ファイルが、それぞれ**何をしているか**のまとめです。
HTML 側は [templates.md](templates.md)、全体の仕組みは [learning-notes.md](learning-notes.md) を参照してください。

---

## 全体の関係

```
manage.py ─→ config/settings.py（設定）
                 ├ config/urls.py ─→ hanken/urls.py ─→ hanken/views.py
                 ├ config/wsgi.py / asgi.py（本番サーバーの入口）
                 └ INSTALLED_APPS "hanken" ─→ hanken/apps.py, models.py, admin.py

hanken/views.py（画面の処理）
   ├ forms.py     入力チェック・保存・写真の縮小
   ├ models.py    データ（Entry）
   ├ analysis.py  集計
   └ emotions.py  気持ちなどの定義

テンプレート ─→ templatetags/hanken_tags.py（表示用フィルタ）
テスト       ─→ tests.py
```

依存の土台は `emotions.py`（他のファイルを import しない）で、上に行くほど多くのファイルを使います。

| 層 | ファイル | ひとことで |
|---|---|---|
| 土台・設定 | `manage.py`、`config/*.py` | 起動と設定 |
| 定義 | `hanken/emotions.py` | 選択肢の一覧 |
| データ | `hanken/models.py` | 半券のテーブル |
| 入力 | `hanken/forms.py` | フォーム・チェック・保存 |
| 計算 | `hanken/analysis.py` | 平均・ランキング・グラフ |
| 画面 | `hanken/views.py`、`urls.py` | URL ごとの処理 |
| 表示補助 | `hanken/templatetags/hanken_tags.py` | テンプレート用フィルタ |
| 管理 | `hanken/admin.py`、`apps.py` | 管理画面・アプリ設定 |
| 確認 | `hanken/tests.py` | 自動テスト |

---

## config/（プロジェクトの設定と入口）

### manage.py
コマンドの入口です。`runserver`、`migrate`、`test`、`createsuperuser` などは全部ここから実行します。

- `DJANGO_SETTINGS_MODULE` を `config.settings` にする
- 受け取ったコマンドを Django に渡す（`execute_from_command_line`）

### config/settings.py
アプリ全体の設定です。

| 設定 | 内容 |
|---|---|
| `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` | 環境変数から読む。なければ開発用の値（本番では必ず環境変数で設定） |
| `INSTALLED_APPS` | Django 標準アプリ（admin、auth、sessions など）＋ `hanken` |
| `MIDDLEWARE` | 毎リクエストで通る処理（セッション、CSRF、ログインユーザーなど） |
| `TEMPLATES` | テンプレートの場所（`templates/`） |
| `DATABASES` | SQLite（`db.sqlite3`） |
| `LANGUAGE_CODE` / `TIME_ZONE` | 日本語・日本時間 |
| `STATIC_*` | CSS/JS の場所と `collectstatic` の出力先 |
| `MEDIA_*` | 写真の保存先（`media/`） |
| `LOGIN_URL` など | ログイン画面・ログイン後・ログアウト後の移動先 |
| `HANKEN_PHOTO_MAX_BYTES` / `HANKEN_PHOTO_MAX_SIDE` | このアプリ独自の設定：写真は1枚10MBまで、保存時は長辺1280px |
| `HANKEN_WORK_IMAGE_MAX_SIDE` | 「最近の作品」の画像は長辺800px |

### config/urls.py
URL の入口の表です。

| URL | 行き先 |
|---|---|
| `admin/` | Django の管理画面 |
| `accounts/signup/` | `views.signup`（登録だけ自作） |
| `accounts/` | Django 標準のログイン・ログアウトなど |
| それ以外 | `hanken/urls.py` に任せる |

`DEBUG` のときだけ、`/media/` の写真を配信する設定を追加します。

### config/wsgi.py / config/asgi.py
本番用サーバーの入口です。どちらも設定を読み込んで `application` を作るだけの短いファイルです。

- `wsgi.py`：Gunicorn、Waitress などが使う
- `asgi.py`：Uvicorn、Daphne などが使う
- `runserver` で開発しているあいだは使わない

---

## hanken/（アプリ本体）

### emotions.py：選択肢の定義
アプリで使う「選べるもの」の一覧です。他のファイルを一切 import しない、いちばん下の土台です。

| 名前 | 中身 | 使う場所 |
|---|---|---|
| `EMOTIONS` | 気持ち10種（キー、表示名、半券の1文字）。例：`("anxious", "不安", "憂")` | analysis |
| `EMOTION_CHOICES` | `(キー, 表示名)` のリスト | models、forms |
| `EMOTION_NAME` / `EMOTION_CHAR` | キー → 表示名／1文字 の辞書 | views、analysis、hanken_tags |
| `KIND_CHOICES` / `KIND_NAME` | 作品の種類：本・映画・ドラマ | models、forms、hanken_tags |
| `SHARE_CHOICES` | 共有：名前つきで共有・匿名で共有・自分だけ | models、forms |
| `MOOD_WORDS` | 気分1〜10の言葉（1＝とてもつらい … 10＝最高） | hanken_tags |

気持ちの10種：嬉しい・ワクワク・穏やか・じんとする・寂しい・悲しい・不安・イライラ・疲れた・ぼんやり

`EMOTIONS` を1つ書けば、`EMOTION_CHOICES`・`EMOTION_NAME`・`EMOTION_CHAR` が自動で作られます。定義を1か所にまとめているので、気持ちを増やすときもここに1行足すだけで済みます（色は `style.css` に追加が必要）。

### models.py：半券と作品のデータ
DB の `hanken_entry` テーブルになる `Entry`（半券1枚）と、`hanken_work` テーブルになる `Work`（管理画面で登録する作品）を定義しています。

**Work（作品）**

| 項目 | 内容 |
|---|---|
| `kind` / `title` | 種類（本・映画・ドラマ）、作品名。同じ種類で同じ作品名は登録できない |
| `note` | ひとこと紹介（なくてもよい） |
| `url` | リンク（公式サイト・配信ページ・販売ページなど。なくてもよい）。`http://` `https://` などの正しいURLだけ保存できる |
| `image` | 画像（表紙・ポスターなど。なくてもよい）。DB には `works/種類/ランダム32文字.jpg` というパスだけが入り、ファイルは `media/works/` に保存される（`work_image_path()` で決める） |
| `image_url` | 画像URL（ほかのサイトの画像アドレス。なくてもよい）。500文字まで。正しいURLだけ保存できる |
| `cover_url` | プロパティ。**表示する画像のURL**：アップロードした `image` があればそれ、なければ `image_url`、どちらもなければ空 |
| `match(kind, title)` | クラスメソッド。**作品名が一致する作品**を探す（前後の空白・英字の大小は無視）。同じ種類を優先し、なければ種類違いでも同名のもの |
| `created_at` / `updated_at` | 登録日時、更新日時（保存するたびに自動で更新） |

並び順は更新日時の新しい順。「最近の作品」画面で使います。

**Entry（半券）**

**項目**

| グループ | 項目 | 内容 |
|---|---|---|
| 共通 | `user` | 記録した人（`auth_user` への外部キー）。ユーザーを消すと半券も消える（`CASCADE`） |
| | `work` | 結びついた作品（`hanken_work` への外部キー。なくてもよい）。作品を消しても半券は残り、空になる（`SET_NULL`）。結びつくと、半券に作品のリンクと画像が出る |
| | `kind` / `title` | 種類、作品名（80文字まで） |
| | `share` | 共有のしかた（初期値：名前つき） |
| | `created_at` | 作成日時（自動） |
| 観る前 | `before_emo` / `before_mood` | 気持ち（必須）、気分 1〜10（必須） |
| | `before_note` / `before_photo` / `before_at` | ひとこと、写真、記録日時 |
| 観た後 | `after_emo` / `after_mood` | 気持ち、気分（**空でもよい**＝鑑賞中） |
| | `after_note` / `after_photo` / `after_at` | ひとこと、写真、記録日時 |

**機能**

| 名前 | 種類 | 機能 |
|---|---|---|
| `photo_path()` | 関数 | 写真の保存先を `photos/年/月/ランダム32文字.jpg` にする（元のファイル名は使わない） |
| `MOOD` | 定数 | 気分を1〜10に制限するチェック |
| `Meta` | 設定 | 新しい順に並べる。管理画面での名前「半券」。`share` と `before_emo` で検索を速くする索引 |
| `__str__()` | メソッド | 管理画面などでの表示「作品名（映画）」 |
| `is_done` | プロパティ | 観た後まで記録済みか |
| `delta` | プロパティ | 気分の変化（観た後 − 観る前）。未記録なら `None` |
| `finished_on` | プロパティ | 観終わった日（日本時間の日付）。観た後を記録した日時から求める。未記録なら `None`。カレンダーで使う |
| `is_shared` | プロパティ | 共有しているか（今は未使用） |
| `delete_photos()` | メソッド | 写真ファイルを `media/` から削除する |

### forms.py：入力・チェック・保存
画面から送られた値を確かめて、半券として保存します。

**部品**

| 名前 | 機能 |
|---|---|
| `RangeInput` | 気分の入力をスライダー（`<input type="range">`）にする |
| `shrink_photo()` | **写真の縮小**：スマホ写真の向きを直し、長辺1280pxの JPEG（品質85）に作り直す。撮影場所などの EXIF 情報は残らない。`side` を渡すと長辺を変えられる（作品の画像は800px） |
| `emo_field()` / `mood_field()` / `photo_field()` / `note_field()` | 同じ設定の入力欄を何度も書かないための作成関数 |
| `PhotoSizeMixin` | 写真が10MBを超えていたらエラーにする |
| `PhaseMixin` | 観る前／観た後の入力欄を1つの辞書にまとめる（`_phase.html` で使う）。`after_phase` を持つ |

**フォーム**

| フォーム | 使う画面 | 機能 |
|---|---|---|　
| `RecordForm` | 記録する | 種類・作品名・観る前・（観た後）・共有を受け取る |
| | | `before_phase`：観る前の入力欄のまとめ |
| | | `clean()`：「もう観終わった」にチェックしたのに、観た後の気持ちや気分がなければエラー |
| | | `save(user)`：`Entry` を作って保存。`Work.match()` で作品名が一致する作品に結びつける。写真は縮小。チェックがあれば観た後も同時に保存 |
| `AfterForm` | 観た後を記録 | 観た後の4項目を受け取る（気持ち・気分は必須） |
| | | `save(entry)`：既存の半券に観た後を書き足す。写真を変えたら古いファイルを消して差し替え |
| `ShareForm` | わたしの半券 | 共有のしかたを1つ受け取る |
| `SignupForm` | 登録 | Django 標準の `UserCreationForm` を使い、項目は「ニックネーム（ログインID）」とパスワード2回だけ |

### analysis.py：集計
半券のリストを受け取り、**テンプレートにそのまま渡せる形**（辞書やリスト）で結果を返します。DB には触らず、Python で計算します。

| 関数 | 使う画面 | 機能 | 返すもの |
|---|---|---|---|
| `summarize()` | わたしの半券、みんなの変化 | 記録済みの半券の件数・平均変化・上がった割合 | `{"n", "avg", "up_pct"}` |
| `before_counts()` | みんなの変化 | 観る前の気持ちごとの件数（0件は除く） | 気持ち選択のチップ用リスト |
| `after_distribution()` | みんなの変化 | 観た後の気持ちの分布。一番多いものを100%とした割合 | 横棒グラフ用リスト |
| `work_ranking()` | みんなの変化 | 作品ごとの平均変化のランキング（上位6）。「X」と「x 」は同じ作品として数える | 作品ランキング用リスト |
| `comfort_works()` | わたしの半券 | 自分の記録で気分が上がった作品（上位3） | 「心のお守り作品」用リスト |
| `slope_chart()` | わたしの半券 | 最近10件の気分の線グラフの座標を計算。重なりを避けるため少しずらす | SVG を描くための座標・目盛り |
| `month_calendar()` | カレンダー | 観る前＋観た後がそろった半券を1枚として、観終わった日ごとに数える（日曜はじまり） | 週ごとの日付マス・月の合計・記録した日数 |
| `care_line()` | ふり返り | 気分の変化に合わせたひとこと | 文章 |

`care_line()` の分かれ方：

| 変化 | ひとこと |
|---|---|
| +3以上 | 心をしっかり軽くしてくれた。思い出せるように残しておこう |
| +1〜+2 | 少しだけ上向いた。自分をいたわれた証拠 |
| ±0 | 数字が変わらなくても、気持ちの色が変わることがある |
| マイナス | 心が動いた分、疲れることもある。ゆっくり休んで |

### views.py：画面ごとの処理
URL ごとに呼ばれ、データを集めてテンプレートを返します。`signup` 以外はすべて `@login_required`（ログイン必須）です。

| 関数 | URL | 機能 |
|---|---|---|
| `author_label()` | （補助） | 半券の表示名を決める：自分なら「あなた」、匿名なら「匿名さん」、それ以外はニックネーム |
| `own_label()` | （補助） | 自分の半券の共有の状態（「自分だけ」「匿名で共有中」「共有中」） |
| `shift_month()` | （補助） | 前の月・次の月を求める（12月の次は翌年1月） |
| `record()` | `/` | 記録画面の表示と保存。観終わっていればふり返りへ、そうでなければメッセージを出して記録画面へ |
| `add_after()` | `/entry/<id>/after/` | 観た後の記録。記録済みなら前の値を入れて表示。保存後はふり返りへ |
| `reflect()` | `/entry/<id>/reflect/` | 変化とケアのひとことを表示。観た後が未記録なら記録画面へ |
| `mine()` | `/mine/` | 自分の半券を鑑賞中／見終わったに分け、集計・お守り作品・グラフを用意 |
| `change_share()` | `/entry/<id>/share/` | 共有のしかたを変更（POST のみ） |
| `delete_entry()` | `/entry/<id>/delete/` | 写真ファイルごと半券を削除（POST のみ） |
| `share()` | `/share/` | 共有された半券を集め、選んだ「観る前の気持ち」で絞り込んで集計 |
| `recent()` | `/recent/` | 管理画面で登録した作品を、映画・本・ドラマごとに更新日時の新しい順で10件ずつ表示。**ログイン・登録の直後に表示される**。時間で移動はせず、「記録をはじめる」で記録画面へ |
| `calendar()` | `/calendar/?m=2026-10&d=17` | 自分の半券を月のカレンダーで数える。`m` で月、`d` で日を選ぶと、その日に観終わった半券も表示。おかしな値は今月として扱う |
| `signup()` | `/accounts/signup/` | ユーザー登録してそのままログイン。ログイン済みなら記録画面へ |

安全のための工夫：
- 半券を1件取るときは、いつも `get_object_or_404(Entry, pk=pk, user=request.user)`。**他人の半券**は存在しない扱い（404）になり、見ることも消すこともできない
- 変更・削除は `@require_POST`。URL を開いただけでは実行されない
- 保存に成功したら `redirect`（再読み込みでの二重送信を防ぐ）

### urls.py：アプリ内の URL 表
`app_name = "hanken"` なので、テンプレートや view からは `hanken:record`、`hanken:mine` のような名前で呼びます。

| URL | 名前 | view |
|---|---|---|
| `""` | `record` | `record` |
| `mine/` | `mine` | `mine` |
| `share/` | `share` | `share` |
| `calendar/` | `calendar` | `calendar` |
| `recent/` | `recent` | `recent` |
| `entry/<int:pk>/after/` | `after` | `add_after` |
| `entry/<int:pk>/reflect/` | `reflect` | `reflect` |
| `entry/<int:pk>/share/` | `change_share` | `change_share` |
| `entry/<int:pk>/delete/` | `delete` | `delete_entry` |

`<int:pk>` は数字だけを受け取り、view に `pk` として渡します。

### templatetags/hanken_tags.py：表示用フィルタ
テンプレートで `{% load hanken_tags %}` と書くと使えるフィルタです。

| フィルタ | 機能 | 例 |
|---|---|---|
| `emo_name` | 気持ちのキー → 名前 | `anxious` → 不安 |
| `emo_char` | 気持ちのキー → 1文字 | `anxious` → 憂 |
| `kind_name` | 種類のキー → 名前 | `movie` → 映画 |
| `mood_word` | 気分の数値 → 言葉 | `7` → いい感じ |
| `signed` | 符号つきの数値 | `4` → +4、`-2` → −2、`0` → ±0。`signed:1` で +1.5 |
| `trend` | CSS のクラス名 | プラス → up、マイナス → down、0 → flat |

### admin.py：管理画面
`/admin/` で半券と作品を管理するための設定です。

**作品（WorkAdmin）**：画像の小さなプレビュー・作品名・種類・紹介・リンクの有無（✓／✗）・更新日時の一覧、種類で絞り込み、作品名で検索。編集画面では種類・作品名・紹介・リンク・画像・画像URLを入力し、「いま表示される画像」でプレビューと、どちら（アップロード／画像URL）が使われているかを確認できる。ここで追加・編集した作品が「最近の作品」に並びます。

| 部品 | 機能 |
|---|---|
| `WorkAdminForm.clean_image()` | 画像が10MBを超えていたらエラー |
| `save_model()` | 画像を変えたときだけ、`shrink_photo()` で長辺800px（`HANKEN_WORK_IMAGE_MAX_SIDE`）の JPEG に縮小して保存。差し替え・クリアしたら古いファイルを消す。最後に、まだ作品に結びついていない同名の半券を結びつける（作品をあとから登録した場合のため） |
| `delete_model()` / `delete_queryset()` | 作品を削除したら画像ファイルも消す（1件ずつ・まとめて削除の両方） |
| `thumb()` / `preview()` | 一覧と編集画面に、`cover_url`（実際に表示される画像）を表示 |

**半券（EntryAdmin）**

| 設定 | 機能 |
|---|---|
| `list_display` | 一覧に出す列（作品名、種類、ユーザー、前後の気持ちと気分、共有、作成日時） |
| `list_filter` | 右側の絞り込み（種類、共有、前後の気持ち） |
| `search_fields` | 作品名とユーザー名で検索 |
| `date_hierarchy` | 作成日時で年・月・日をたどれる |

### apps.py：アプリの設定
`HankenConfig`：アプリ名 `hanken`、管理画面での表示名「感情の半券」、id の型を決めています。

### migrations/0001_initial.py
`models.py` から自動生成された、テーブルを作る手順です。`0002_work.py` は作品テーブルを追加したとき、`0003_work_url.py` は作品にリンクを、`0004_work_image.py` は作品に画像を、`0005_work_image_url.py` は作品に画像URLを追加したときのものです。`0006_entry_work.py` は半券に作品を結びつける項目を追加し、すでにある半券も同名の作品に結びつけます（`RunPython` でデータも処理する例）。`python manage.py migrate` で実行されます。**手で編集しません**。`models.py` を変えたら `makemigrations` で新しいファイルを作ります。

### tests.py：自動テスト
`python manage.py test hanken` で実行される19件のテストです。

**準備用の関数**
- `make()`：テスト用の半券をすぐ作る
- `png()`：2000×1000 のテスト画像を作る

**AnalysisTests（集計）**

| テスト | 確かめていること |
|---|---|
| `test_summary_and_ranking` | 平均変化・上がった割合が正しい。「X」と「x 」が同じ作品になる |
| `test_open_entries_are_ignored` | 鑑賞中の半券は集計・グラフに入らない |

**ViewTests（画面）**

| テスト | 確かめていること |
|---|---|
| `test_login_required` | ログインしていないとリダイレクトされる |
| `test_record_before_then_after` | 観る前→観た後の流れ。写真が JPEG になり長辺1280pxに縮む。ふり返りに「+5」が出る |
| `test_both_requires_after_emotion` | 「もう観終わった」なのに観た後の気持ちがないとエラーで、保存されない |
| `test_share_page_hides_private_and_anonymizes` | 「自分だけ」は出ない、匿名は「匿名さん」になる、集計は共有分だけ |
| `test_cannot_touch_others_entries` | 他人の半券は削除も編集もできない（404） |
| `test_mine_page_and_delete` | わたしの半券の表示、共有の変更、削除 |
| `test_calendar_counts_finished_stubs` | カレンダーは前後そろった自分の半券だけを数える（鑑賞中・他人の分は数えない）。日付を選ぶとその日の半券が出る |
| `test_calendar_ignores_bad_params` | 13月・存在しない日付などでもエラーにならない |
| `test_recent_works_lists_ten_newest_per_kind` | 最近の作品は映画・本・ドラマの順に、更新日時の新しい10件ずつ。自動で移動する設定はない |
| `test_recent_works_link` | リンクがある作品だけ作品名がリンクになり、別のタブで開く。`javascript:` のリンクは保存できない |
| `test_work_image_upload_from_admin` | 管理画面から画像を登録すると、長辺800pxの JPEG になって最近の作品に表示される。差し替え・削除で古いファイルが消える |
| `test_work_cover_prefers_upload_over_image_url` | 画像URLだけならそれを表示、アップロードした画像があればそちらを優先。`javascript:` は保存できない |
| `test_new_entry_links_to_matching_work` | 半券を追加すると同名の作品に結びつき（同じ種類を優先、種類違いでも可）、作品のリンクと画像が半券に出る。一致しなければ結びつかない |
| `test_work_added_later_links_existing_entries` | 作品をあとから登録すると、同名の半券（英字の大小違いも）が結びつく。作品を消しても半券は残る |
| `test_admin_tab_only_for_staff` | 「管理画面」のタブは管理者にだけ表示される |
| `test_login_goes_to_recent_works` | ログインすると最近の作品へ移動する |
| `test_signup` | 登録すると最近の作品へ移動する |

テストは本物の `db.sqlite3` を使わず、テスト用の DB を毎回作って最後に消します。

---

## 機能から探す

| やりたいこと・知りたいこと | 見るファイル |
|---|---|
| 気持ちの種類を増やす | `emotions.py`（＋ `style.css` の色） |
| 半券に項目を増やす | `models.py` → `makemigrations` → `forms.py` → テンプレート |
| 入力チェックを変える | `forms.py` |
| 写真のサイズ・画質を変える | `settings.py` の `HANKEN_PHOTO_*`、`forms.py` の `shrink_photo()` |
| 集計やグラフを変える | `analysis.py` |
| ケアのひとことを変える | `analysis.py` の `care_line()` |
| 新しい画面を作る | `urls.py` → `views.py` → テンプレート |
| 匿名のときの表示名を変える | `views.py` の `author_label()` |
| テンプレートの表示形式を変える | `templatetags/hanken_tags.py` |
| 本番の設定 | `config/settings.py`（環境変数） |
| 動作を確かめる | `tests.py` |
