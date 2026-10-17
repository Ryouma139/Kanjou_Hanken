# 感情の半券（Django版）

本・映画・ドラマを観る**前**と**後**の気持ちを、写真つきの「半券」に記録するアプリです。
同じ気持ちで観始めた人が、観たあとどう変わったかを集計して共有できます。

## 起動方法

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # 管理画面を使う場合（任意）
python manage.py runserver
```

ブラウザで http://127.0.0.1:8000/ を開き、「はじめての方はこちら」から登録します。

テスト: `python manage.py test hanken`

## 画面

| URL | 画面 |
|---|---|
| `/` | 記録する（作品・観る前の気持ち・写真・共有範囲。「もう観終わった」で観た後も同時に記録） |
| `/entry/<id>/after/` | 観た後を記録する |
| `/entry/<id>/reflect/` | ふり返り（気持ちの変化とメンタルケアのひとこと） |
| `/mine/` | わたしの半券（平均変化・気分の動きのグラフ・心のお守り作品・共有設定の変更・削除） |
| `/share/?emo=anxious` | みんなの変化（観る前の気持ち別に、観た後の気持ちの分布・作品ランキング・最近の半券） |
| `/admin/` | Django管理画面 |

## 構成

```
config/            設定・URL
hanken/
  emotions.py      気持ち10種・作品の種類・共有範囲の定義
  models.py        Entry（1枚の半券）
  forms.py         記録フォーム。写真は向きを補正し長辺1280pxのJPEGに縮小して保存
  analysis.py      集計（平均変化・分布・作品ランキング・グラフ座標・ケアの文言）
  views.py         画面
  templatetags/    表示用フィルタ（気持ちの名前、+4/−2 表記など）
templates/         画面のHTML
static/hanken/     CSS と小さなJavaScript（スライダー表示・写真プレビューなど）
```

## 共有のルール

- **名前つきで共有**：「みんなの変化」にニックネームつきで表示・集計されます。
- **匿名で共有**：「匿名さん」として表示・集計されます。
- **自分だけ**：自分の画面にだけ表示され、集計にも使われません。

## 本番公開するとき

- 環境変数 `DJANGO_SECRET_KEY`、`DJANGO_DEBUG=0`、`DJANGO_ALLOWED_HOSTS` を設定してください。
- `python manage.py collectstatic` を実行し、静的ファイルとアップロード写真（`media/`）をWebサーバーから配信してください。
- 写真のファイル名は推測しにくい名前にしていますが、URLを知っていれば誰でも見られます。
  「自分だけ」の写真を厳密に守る場合は、ログイン確認つきのビュー経由で配信してください。
