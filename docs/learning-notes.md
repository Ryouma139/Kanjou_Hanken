# 感情の半券 学習ノート

このアプリ（Django製）の仕組みを、質問しながら確認した内容のまとめです。

---

## 1. 起動とGitHub

### 起動のしかた
```powershell
.\.venv\Scripts\activate
python manage.py runserver
```
- http://127.0.0.1:8000/ を開く
- 管理画面 `/admin/` を使うときは、先に `python manage.py createsuperuser` を実行する
- テスト：`python manage.py test hanken`（9件）

### 起動時の WARNING
```
WARNING: This is a development server. Do not use it in a production setting.
```
エラーではなく、`runserver` が毎回出す注意書き。開発用の簡易サーバーなので、本番公開には使わないという意味。

### GitHub
- リポジトリ：https://github.com/Ryouma139/Kanjou_Hanken
- このフォルダで独立したリポジトリとして `git init` した（ブランチ `main`）
- [.gitignore](../.gitignore) で除外しているもの：`.venv/`、`db.sqlite3`、`__pycache__/`、`media/`、`staticfiles/`、`.env`
- プッシュ：`git push -u origin main`

---

## 2. フォルダ構成と5つの層

各 `.py` ファイルの機能は [python-files.md](python-files.md) にまとめてある。

```
⑤ 見た目       templates/  static/
④ 画面の処理   views.py  urls.py  forms.py
③ 計算         analysis.py  templatetags/
② データ       emotions.py  models.py  migrations/
① 土台・設定   manage.py  config/
```

| フォルダ | 役割 |
|---|---|
| `config/` | プロジェクト全体の設定（settings.py、全体の urls.py、wsgi.py、asgi.py） |
| `hanken/` | アプリ本体（半券を記録・集計する機能） |
| `templates/` | 画面のHTML |
| `static/hanken/` | CSS と JavaScript |
| `.venv/` | インストールしたライブラリ（Django、asgiref など）。**編集しない** |

### Djangoアプリ（hanken）の決まったファイル名
Django は名前を頼りにファイルを探すので、名前は変えられない。

| ファイル | 役割 |
|---|---|
| `models.py` | データの形（DBのテーブル） |
| `views.py` | 画面ごとの処理 |
| `urls.py` | URL と view の対応 |
| `forms.py` | 入力フォーム・入力チェック |
| `admin.py` | 管理画面の設定 |
| `apps.py` | アプリ自身の設定 |
| `migrations/` | DB の変更履歴 |
| `tests.py` | テスト |
| `templatetags/` | テンプレート用の自作フィルタ |

[config/settings.py](../config/settings.py) の `INSTALLED_APPS` に `"hanken"` があるので、起動時に Django が `apps.py` → `models.py` を自動で読み込む。

---

## 3. 実行順序

### ① 起動時（`python manage.py runserver`）
1. [manage.py](../manage.py) が `DJANGO_SETTINGS_MODULE = config.settings` を設定する
2. [config/settings.py](../config/settings.py) を読み込む
3. `INSTALLED_APPS` のアプリを読み込む（`hanken/models.py` もここ）
4. [config/urls.py](../config/urls.py) と [hanken/urls.py](../hanken/urls.py) の URL 表を準備する
5. http://127.0.0.1:8000/ で待ち受けを始める

### ② リクエスト1回ごと
```
ブラウザ  GET /mine/
  ↓
MIDDLEWARE（settings.py の上から順）
  セッション読込 → CSRF確認 → ログインユーザー特定 → メッセージ準備
  ↓
config/urls.py → hanken/urls.py で URL を照合
  ↓
views.py の関数（例：mine）
  @login_required：未ログインなら /accounts/login/ へ
  models.py（Entry）で DB を読み書き
  analysis.py で集計、forms.py で入力チェック・写真の縮小
  ↓
templates/ の HTML に値を埋め込む（base.html ＋ hanken/mine.html）
  ↓
MIDDLEWARE を逆順に通る
  ↓
ブラウザに HTML を返す → CSS/JS（static/hanken/）を別に取得
```

### ③ ユーザーの操作の流れ
| 順 | URL | view | 内容 |
|---|---|---|---|
| 1 | `/accounts/signup/` | `signup` | 登録してログイン |
| 1' | `/accounts/login/` | Django標準 | ログイン |
| 2 | `/` | `record` | 作品と観る前の気持ちを記録。「観終わった」なら観た後も一緒に |
| 3 | `/entry/<id>/after/` | `add_after` | 観た後の気持ちを記録 |
| 4 | `/entry/<id>/reflect/` | `reflect` | 気持ちの変化とケアのひとこと |
| 5 | `/mine/` | `mine` | 自分の半券一覧・グラフ。共有変更（`change_share`）・削除（`delete_entry`） |
| 6 | `/share/?emo=...` | `share` | みんなの変化。観る前の気持ち別に集計 |

```
登録/ログイン → 記録(/) ─観終わった→ ふりかえり(reflect) → わたしの半券(mine)
                  └─まだ→ 後で after → reflect
                                   みんなの変化(share)
```

---

## 4. URL の仕組み

### URL はフォルダではない
`/accounts/login/` や `/mine/` に対応するフォルダは存在しない。URL は **urls.py の表** で決まる。

```
/accounts/login/
  → config/urls.py      path("accounts/", include("django.contrib.auth.urls"))
  → django/contrib/auth/urls.py   path("login/", LoginView.as_view(), name="login")
  → LoginView（Python のクラス）が実行される
```
`"accounts/"` を `"member/"` に変えれば、`/member/login/` になる。

例外として、ファイルをそのまま配信する2つだけはフォルダと対応する：
- `/static/hanken/app.js` → `static/hanken/app.js`
- `/media/photos/...` → `media/photos/...`

### /accounts/login/（Django標準のログイン機能）
`include("django.contrib.auth.urls")` で追加される URL：

| URL | name | 役割 |
|---|---|---|
| `/accounts/login/` | `login` | ログイン |
| `/accounts/logout/` | `logout` | ログアウト（POST のみ） |
| `/accounts/password_change/` | `password_change` | パスワード変更 |
| `/accounts/password_reset/` | `password_reset` | パスワード再設定（※このアプリでは未対応） |

関係する設定（[config/settings.py](../config/settings.py)）：
```python
LOGIN_URL = "login"                    # @login_required が飛ばす先
LOGIN_REDIRECT_URL = "hanken:record"   # ログイン後の移動先
LOGOUT_REDIRECT_URL = "login"          # ログアウト後の移動先
```
- 未ログインで `/mine/` を開くと `/accounts/login/?next=/mine/` に移動し、ログイン後は `/mine/` に戻る
- 見た目は [templates/registration/login.html](../templates/registration/login.html)。`LoginView` がこの決まった名前を探す

実体のファイル：
- URL の表：`.venv/Lib/site-packages/django/contrib/auth/urls.py`
- 処理：`.venv/Lib/site-packages/django/contrib/auth/views.py`

---

## 5. hanken の中の呼び出し方

### Python ファイル同士（import）
```
                 emotions.py   ← 土台（気持ち10種・作品の種類・共有範囲の定義）
               ↗    ↑     ↑    ↖
       models.py analysis.py  templatetags/hanken_tags.py
        ↑    ↑        ↑
  forms.py  admin.py  │
        ↑             │
        views.py ─────┘   ← models・forms・analysis・emotions を全部使う
        ↑
        urls.py           ← views だけを使う
```

書き方：
```python
from . import analysis                # 同じフォルダの analysis.py をモジュールごと
from .emotions import EMOTION_NAME    # emotions.py の中の EMOTION_NAME だけ
from ..emotions import ...            # 1つ上のフォルダ（templatetags から使うとき）
```
- `.` は同じフォルダ、`..` は1つ上のフォルダ
- `from . import analysis` なら `analysis.summarize(done)` のように呼ぶ
- import の `.` はフォルダの区切りに対応する（`django.contrib.auth.decorators` → `django/contrib/auth/decorators.py`）

### テンプレート同士
| タグ | 意味 |
|---|---|
| `{% extends "base.html" %}` | 共通の外枠を継承する |
| `{% include "..." with x=... %}` | 部品を差し込む |

### テンプレートから Python 側を呼ぶ
| タグ | 呼び出し先 |
|---|---|
| `{% load hanken_tags %}` | 自作フィルタを使えるようにする |
| `{% url 'hanken:mine' %}` | hanken/urls.py の `name="mine"` から URL を作る |
| `{% static 'hanken/style.css' %}` | static ファイルの URL を作る |

### Django が自動で呼ぶもの
`apps.py`、`models.py`、`admin.py`、`tests.py`、`templatetags/` は、どこからも import されていないが、Django が決まった名前で探して呼び出す。

---

## 6. テンプレート（templates/）

各HTMLの詳しい中身は [templates.md](templates.md) にまとめてある。

### 置き場所と探し方
[config/settings.py](../config/settings.py)：
```python
"DIRS": [BASE_DIR / "templates"],   # プロジェクト直下の templates/
"APP_DIRS": True,                   # 各アプリの中の templates/ も探す
```

### 対応表
| テンプレート | 呼んでいる場所 | 呼び方 |
|---|---|---|
| `base.html` | すべての画面テンプレート | `{% extends %}`（外枠） |
| `hanken/record.html` | `views.record()` | `render()` |
| `hanken/after.html` | `views.add_after()` | `render()` |
| `hanken/reflect.html` | `views.reflect()` | `render()` |
| `hanken/mine.html` | `views.mine()` | `render()` |
| `hanken/share.html` | `views.share()` | `render()` |
| `registration/signup.html` | `views.signup()` | `render()` |
| `registration/login.html` | Django標準の `LoginView` | 自動 |
| `hanken/_stub.html` | mine / share / reflect | `{% include %}`（部品） |
| `hanken/_half.html` | `_stub.html` | `{% include %}`（部品） |
| `hanken/_phase.html` | record / after | `{% include %}`（部品） |

```
views.py
 ├ record()    → record.html  ─include→ _phase.html
 ├ add_after() → after.html   ─include→ _phase.html
 ├ reflect()   → reflect.html ─include→ _stub.html ─include→ _half.html
 ├ mine()      → mine.html    ─include→ _stub.html ─include→ _half.html
 ├ share()     → share.html   ─include→ _stub.html ─include→ _half.html
 └ signup()    → registration/signup.html
Django標準 LoginView → registration/login.html
```

### 部品（`_` で始まるもの）
- `_stub.html`：半券1枚。`own`、`manage` でボタンを出すか切り替える
- `_half.html`：半券の片側（BEFORE／AFTER）
- `_phase.html`：入力フォームの片側（観る前／観た後）

### base.html
全画面共通の外枠。
- `<head>`：フォントと `style.css`
- ヘッダー：タイトル、ユーザー名、ログアウトボタン
- タブ（view から渡された `tab` で強調）
- メッセージ表示
- `{% block content %}`：**各画面の中身が入る場所**
- `</body>` 直前で `app.js`

---

## 7. render と redirect

```python
return render(request, "テンプレート名", {渡すデータ})
```
| 引数 | 意味 |
|---|---|
| `request` | 今のリクエスト（ログインユーザー、CSRF トークンなど） |
| `"hanken/reflect.html"` | `templates/` からの相対パス |
| `{...}` | テンプレートに渡す値（コンテキスト） |

render の中で起きること：
1. テンプレートを templates/ から探す
2. extends / include をたどって合体させる
3. `{{ }}` や `{% %}` を値で置き換えて HTML を完成させる
4. HttpResponse に包んで返す

| | 何を返すか | 使う場面 |
|---|---|---|
| `render` | HTML そのもの | 画面表示（GET、入力エラー時の再表示） |
| `redirect` | 「別の URL へ移動して」という指示（302） | 保存が成功したあと（POST の後） |

保存後に redirect するのは、再読み込みでフォームが二重送信されるのを防ぐため。

---

## 8. @（デコレータ）と login_required

`@` は関数の中身を変えずに、前後に処理を追加する書き方。

```python
@login_required        # ログインしていなければログイン画面へ
@require_POST          # POST 以外なら 405 エラー
def delete_entry(request, pk):
    ...
```
| デコレータ | 付いている関数 | 役割 |
|---|---|---|
| `@login_required` | `signup` 以外のすべての view | 未ログインならログイン画面へ |
| `@require_POST` | `change_share`、`delete_entry` | URL を開いただけで削除・変更されるのを防ぐ |

`@login_required` は `mine = login_required(mine)` と同じ意味。デコレータは「関数を受け取って新しい関数を返す関数」。

複数付けたときは、**上から順にチェック**される（ログイン確認 → POST 確認 → 本体）。

### login_required の実体
`.venv/Lib/site-packages/django/contrib/auth/decorators.py` の71行目（Django本体の関数）。
```python
def login_required(...):
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated,   # 判定を渡すだけ
        ...
```
実際のチェックは `user_passes_test` の中：
```python
def _view_wrapper(request, *args, **kwargs):
    test_pass = test_func(request.user)
    if test_pass:
        return view_func(request, *args, **kwargs)   # OK → 元の view を実行
    return _redirect_to_login(request)               # NG → ログイン画面へ
```
- ログイン画面の URL は `settings.LOGIN_URL` から決まる
- `asgiref` を使い、非同期の view にも対応している
- `request.user` を用意しているのは MIDDLEWARE の `AuthenticationMiddleware`

---

## 9. static（CSS・JavaScript）

### 読み込んでいる場所
[templates/base.html](../templates/base.html) の1か所だけ。全画面が base.html を継承するので、全ページで読み込まれる。
```html
{% load static %}
<link rel="stylesheet" href="{% static 'hanken/style.css' %}">   ← <head>の中
<script src="{% static 'hanken/app.js' %}"></script>              ← </body>の直前
```
`{% static %}` は `/static/hanken/app.js` という URL になり、ブラウザが別のリクエストで取得する（views.py は通らない）。

### app.js の処理
| 処理 | 探している要素 | 画面 |
|---|---|---|
| 気分スライダーの数値と言葉 | `input[type=range]`、`data-mood-out` | 記録・観た後 |
| 写真のプレビュー | `input[type=file]`、`data-preview-for` | 記録・観た後 |
| 「もう観終わった」で観た後の欄を出す | `#id_both`、`#after-panel` | 記録 |
| 共有設定を選んだらすぐ保存 | `select[data-autosubmit]` | わたしの半券 |
| 写真が読めないとき気持ちの色で表示 | `.tile img` | 半券の表示 |

どれも補助で、JavaScript が無効でもフォームは動く。

### static と staticfiles
```python
STATIC_URL = "static/"                    # ブラウザから見える URL
STATICFILES_DIRS = [BASE_DIR / "static"]  # 自分で書いた CSS/JS
STATIC_ROOT = BASE_DIR / "staticfiles"    # collectstatic の出力先
```
| フォルダ | 中身 | 役割 |
|---|---|---|
| `static/` | app.js、style.css | **自分で編集する**元ファイル |
| `staticfiles/` | 上＋管理画面の CSS/JS | `collectstatic` が集めたコピー。本番で配信する |

`staticfiles/` は `python manage.py collectstatic` を実行したときに初めて作られる。開発中は不要。

---

## 10. データベース（SQLite）

### 全体の流れ
```
① settings.py      DATABASES：接続先（db.sqlite3）
② models.py        Entry クラス：テーブルの設計図
③ migrations/      CREATE TABLE する手順（migrate で実行）
④ views.py など    Entry.objects.filter(...) で呼び出す
         ↓ Django ORM が SQL に変換
⑤ db.sqlite3       実際のテーブル
```

### テーブル
| 操作 | テーブル | 中身 |
|---|---|---|
| ユーザー登録 | `auth_user` | ユーザー名、パスワード（ハッシュ化）など |
| ログイン | `django_session` | ログイン状態（Cookie と対応） |
| 半券の記録 | `hanken_entry` | 作品名、気持ち、気分、メモ、共有設定、**写真のパス** |
| 写真 | （DB には入らない） | `media/photos/年/月/` にファイル |

- `hanken_entry` は `models.py` の `Entry` から作られる（名前は「アプリ名_クラス名」）
- `auth_user`、`django_session` は Django 標準アプリが用意する
- パスワードは `pbkdf2_sha256$...` のハッシュで保存され、元の文字は分からない
- `auth_permission`、`django_migrations` などは Django の管理用

### アプリ内での呼び出し場所
| テーブル | 場所 | 操作 |
|---|---|---|
| `hanken_entry` | `views.share()`：`Entry.objects.exclude(...)` | SELECT |
| | `views.mine()`：`request.user.entries.all()` | 自分の分を SELECT |
| | `get_object_or_404(Entry, pk=pk, user=request.user)` | 1件（他人のなら404） |
| | `RecordForm.save()`：`entry.save()` | INSERT |
| | `AfterForm.save()`、`change_share()`：`entry.save()` | UPDATE |
| | `delete_entry()`：`entry.delete()` | DELETE |
| `auth_user` | `SignupForm.save()`、ログイン処理 | INSERT・SELECT |
| | `select_related("user")` | JOIN |
| `django_session` | `SessionMiddleware` | 毎リクエスト自動 |

### ORM が作る SQL の例（views.share()）
```python
Entry.objects.exclude(share="private").exclude(after_emo="")
     .filter(after_mood__isnull=False).select_related("user")
```
↓
```sql
SELECT hanken_entry.*, auth_user.*
FROM hanken_entry
INNER JOIN auth_user ON hanken_entry.user_id = auth_user.id
WHERE NOT (share = 'private') AND NOT (after_emo = '') AND after_mood IS NOT NULL
ORDER BY created_at DESC
```
- `select_related("user")` → `INNER JOIN`
- `ORDER BY` は models.py の `Meta` の既定の並び順
- SQL を見るには `print(Entry.objects.filter(...).query)`

### 中身を見る方法
- 管理画面 `/admin/`（おすすめ）
- `python manage.py shell` / `dbshell`
- VS Code 拡張「SQLite Viewer」

### なぜ SQL を書かずに ORM を使うのか
1. **安全**：値は必ずパラメータで渡され、SQL インジェクションを防げる
2. **オブジェクトで返る**：`entry.title`、`entry.delta`、`entry.user.username`、`entry.before_photo.url`
3. **DB を変えてもそのまま動く**：SQLite → PostgreSQL は settings.py の変更だけ
4. **設計とコードがずれない**：models.py → migrate でテーブルも変わる。管理画面・フォームも自動
5. **組み合わせやすい**：条件を少しずつ足せて、最後に1回だけ SQL が実行される

弱点：
- 実際の SQL が見えにくい
- `select_related` を忘れると N+1 問題で遅くなる
- 複雑な集計は SQL の方が素直なこともある（`Entry.objects.raw(...)` や `connection` で直接書ける）

---

## 11. 写真の保存

### 保存場所
```
media/photos/2026/10/（ランダムな32文字）.jpg
```
- `MEDIA_ROOT = BASE_DIR / "media"`（settings.py）
- [hanken/models.py](../hanken/models.py) の `photo_path` でパスを決める。ファイル名は uuid で推測されにくくしている
- DB には「photos/2026/10/xxxx.jpg」というパスだけが入る

### 保存までの流れ
```
写真を選ぶ → POST（request.FILES）
  → forms.py _check_photo()   10MB を超えていないか
  → forms.py shrink_photo()   向き補正、長辺1280px の JPEG（品質85）に縮小
  → entry.before_photo.save() media/ に書き込む
  → entry.save()              DB にパスを記録
```
- 元の画像は保存されない
- JPEG に作り直すので、撮影場所などの EXIF 情報は残らない
- 半券を削除すると `delete_photos()` でファイルも消える。観た後の写真を撮り直すと古いファイルを消してから保存

### 表示
- `{{ e.before_photo.url }}` → `/media/photos/...`
- 開発中は config/urls.py の `if settings.DEBUG:` で runserver が配信
- 本番では Nginx などで `media/` を配信する設定が必要
- URL を知っていれば「自分だけ」の写真も見られる点に注意

---

## 12. 共有のしかた

| 値 | 表記 | みんなの変化の集計 | 最近の半券での名前 |
|---|---|---|---|
| `public` | 名前つき（初期値） | 含まれる | ニックネーム（なければユーザー名） |
| `anon` | 匿名 | 含まれる | 「匿名さん」 |
| `private` | 自分だけ | **含まれない** | 表示されない |

- 集計対象：`views.share()` の `Entry.objects.exclude(share="private")`
- 名前：`views.author_label()`。自分の半券は匿名でも「あなた」と表示
- 変更：`_stub.html` のセレクトボックス → `app.js` の `data-autosubmit` ですぐ送信 → `change_share()`

**注意**：匿名で隠れるのは名前だけ。作品名・気持ち・気分・**メモ・写真**は他の人にも見える。

---

## 13. Python・周辺の用語

### ビルドファイル
Python には「ビルドしてできる実行ファイル」がない。近いもの：
- `__pycache__/*.pyc`：自動生成されるバイトコードのキャッシュ（消しても再生成される）
- `requirements.txt`：必要なライブラリの一覧（Node.js の package.json に相当）
- Django を本番公開するときの手順：`pip install -r requirements.txt` → `migrate` → `collectstatic`

### asgiref
Django の必須の依存ライブラリ（`.venv` の中）。
- ASGI の土台を提供する（[config/asgi.py](../config/asgi.py) が使う）
- `sync_to_async` / `async_to_sync` で同期と非同期の橋渡しをする
- 自分で編集しない。GitHub にも上がらない

### WSGI / ASGI サーバー
| 種類 | 例 | 特徴 |
|---|---|---|
| WSGI | Gunicorn（Linux）、Waitress（Windows）、uWSGI | 普通の同期処理 |
| ASGI | **Uvicorn**、Daphne | 非同期・WebSocket に対応 |

Uvicorn での起動：
```powershell
pip install uvicorn
uvicorn config.asgi:application
```
このアプリは非同期の機能を使っていないので、WSGI でも十分。

### Nginx
今はどこでも動いていない（このPCにも未インストール）。本番公開するサーバーに入れて使う。
```
インターネット ⇄ Nginx ⇄ Gunicorn/Uvicorn ⇄ Django
                  └─ staticfiles/ と media/ を直接配信
```
- Nginx：受付、HTTPS 化、静的ファイルの配信
- Gunicorn/Uvicorn：Django のコードを実行
- Render、Railway、PythonAnywhere などの PaaS なら、Nginx 相当はサービス側が用意する（静的ファイルは `whitenoise` が手軽）

### 本番公開で必要な設定（README より）
- 環境変数 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS`
- `python manage.py collectstatic`
- `staticfiles/` と `media/` を Web サーバーから配信

---

## 14. 学習の進め方

1. **動かして触る**：登録 → 記録 → 観た後 → わたしの半券 → みんなの変化。`/admin/` でデータを見る
2. **データの形を知る**（いちばん大事）：`emotions.py` → `models.py`。半券1枚の項目を書き出せるようにする
3. **1つの画面を端から端まで追う**：
   `urls.py → views.record() → forms.RecordForm → models.Entry → record.html → _phase.html → app.js`
4. **残りの画面を同じ方法で**：`reflect` → `add_after` → `mine` → `share`（`analysis.py` も一緒に）
5. **設定と土台**：settings.py を「今まで出てきたものがどこで設定されているか」の視点で読む
6. **テストを読む**：`tests.py` を読んで `python manage.py test hanken`

### 練習問題（小さい順）
1. `app.js` の `WORDS` を変えて、画面に反映されるか見る
2. `emotions.py` に気持ちを1つ追加する（migration が必要か考える）
3. `Entry` に項目（例：「一緒に観た人」）を追加 → `makemigrations` → フォーム → テンプレート
4. 新しい画面（例：`/stats/`）を urls → views → template の順に作る
5. 3 や 4 のテストを `tests.py` に書く

### 読むときのコツ
- ファイル単位ではなく、**1つの機能を縦に追う**
- Django 本体（`.venv` の中）は「やってくれる部分」と割り切る。読むのはよいが編集しない
- VS Code で Ctrl+クリックして定義に飛ぶ。`print()` を入れて runserver のログで値を確認する
