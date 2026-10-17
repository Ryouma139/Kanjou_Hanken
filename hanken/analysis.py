"""半券の集計。テンプレートにそのまま渡せる形で返す。"""
from collections import Counter, defaultdict

from .emotions import EMOTIONS, EMOTION_NAME


def summarize(entries):
    """完了済みの半券から 件数・平均変化・上がった割合 を出す。"""
    ds = [e.delta for e in entries if e.is_done]
    if not ds:
        return {"n": 0, "avg": 0.0, "up_pct": 0}
    return {
        "n": len(ds),
        "avg": sum(ds) / len(ds),
        "up_pct": round(sum(1 for d in ds if d > 0) / len(ds) * 100),
    }


def before_counts(entries):
    """観る前の気持ちごとの件数（定義順、0件は除く）。"""
    c = Counter(e.before_emo for e in entries)
    return [{"key": k, "name": n, "n": c[k]} for k, n, _ in EMOTIONS if c[k]]


def after_distribution(entries):
    c = Counter(e.after_emo for e in entries if e.is_done)
    if not c:
        return []
    top = max(c.values())
    return [{"key": k, "name": EMOTION_NAME[k], "n": n, "pct": n / top * 100}
            for k, n in c.most_common()]


def work_ranking(entries, limit=6):
    """同じ作品（種類＋作品名、大文字小文字は区別しない）ごとの平均変化。"""
    groups = defaultdict(list)
    names = {}
    for e in entries:
        if not e.is_done:
            continue
        key = (e.kind, e.title.strip().lower())
        groups[key].append(e.delta)
        names.setdefault(key, e.title.strip())
    rows = [{"title": names[k], "kind": k[0], "n": len(v), "avg": sum(v) / len(v)}
            for k, v in groups.items()]
    rows.sort(key=lambda r: (-r["avg"], -r["n"]))
    return rows[:limit]


def comfort_works(entries, limit=3):
    """自分の記録のうち、気分が上がった作品を変化の大きい順に。"""
    ups = [e for e in entries if e.is_done and e.delta > 0]
    ups.sort(key=lambda e: -e.delta)
    return ups[:limit]


# スロープチャート（観る前→観た後）の座標
SLOPE = {"w": 340, "h": 210, "x1": 78, "x2": 262, "top": 30, "bottom": 182}


def _y(mood):
    return SLOPE["bottom"] - (mood - 1) * (SLOPE["bottom"] - SLOPE["top"]) / 9


def slope_chart(entries, limit=10):
    done = [e for e in entries if e.is_done][:limit]
    done.reverse()  # 古い順に描く
    lines = []
    for i, e in enumerate(done):
        jitter = (i % 3 - 1) * 2
        d = e.delta
        lines.append({
            "title": e.title,
            "b": e.before_mood, "a": e.after_mood,
            "yb": round(_y(e.before_mood) + jitter, 1),
            "ya": round(_y(e.after_mood) + jitter, 1),
            "b_emo": e.before_emo, "a_emo": e.after_emo,
            "dir": "up" if d > 0 else "down" if d < 0 else "flat",
        })
    ticks = [{"m": m, "y": round(_y(m), 1)} for m in (1, 5, 10)]
    return {**SLOPE, "lines": lines, "ticks": ticks, "label_y": SLOPE["h"] - 6,
            "tick_x": SLOPE["x1"] - 12}


def care_line(delta):
    if delta >= 3:
        return "この作品は、あなたの心をしっかり軽くしてくれたようです。また同じ気持ちになったとき、思い出せるように残しておきましょう。"
    if delta > 0:
        return "少しだけ気持ちが上向きました。小さな変化も、自分をいたわれた証拠です。"
    if delta == 0:
        return "気分の数字は変わらなくても、気持ちの色が変わることがあります。今日も作品と過ごせたことを記録できました。"
    return "観たあと、少し重くなったようです。心が動いた分、疲れることもあります。今日はゆっくり休んでくださいね。"
