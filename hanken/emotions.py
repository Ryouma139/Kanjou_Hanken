"""気持ち・作品の種類・共有範囲の定義。"""

# (キー, 表示名, 半券に描く一文字)
EMOTIONS = [
    ("joy", "嬉しい", "喜"),
    ("excited", "ワクワク", "躍"),
    ("calm", "穏やか", "穏"),
    ("moved", "じんとする", "感"),
    ("lonely", "寂しい", "寂"),
    ("sad", "悲しい", "哀"),
    ("anxious", "不安", "憂"),
    ("irritated", "イライラ", "苛"),
    ("tired", "疲れた", "疲"),
    ("numb", "ぼんやり", "空"),
]
EMOTION_CHOICES = [(k, n) for k, n, _ in EMOTIONS]
EMOTION_NAME = {k: n for k, n, _ in EMOTIONS}
EMOTION_CHAR = {k: c for k, _, c in EMOTIONS}

KIND_CHOICES = [("book", "本"), ("movie", "映画"), ("drama", "ドラマ")]
KIND_NAME = dict(KIND_CHOICES)

SHARE_CHOICES = [
    ("public", "名前つきで共有"),
    ("anon", "匿名で共有"),
    ("private", "自分だけ"),
]

AD_PLACEMENT_CHOICES = [
    ("footer", "全ページの下"),
    ("reflect", "ふり返り画面"),
    ("recent", "最近の作品"),
]

MOOD_WORDS = ["", "とてもつらい", "つらい", "しんどい", "少し重い", "ふつう",
              "まあまあ", "いい感じ", "良い", "とても良い", "最高"]
