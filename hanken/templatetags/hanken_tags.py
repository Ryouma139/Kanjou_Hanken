from django import template

from ..emotions import EMOTION_CHAR, EMOTION_NAME, KIND_NAME, MOOD_WORDS
from ..models import Ad

register = template.Library()


@register.inclusion_tag("hanken/_ads.html")
def ads(placement):
    """{% ads "footer" %} のように使う。その場所の表示中の広告を「PR」付きで出す。"""
    return {"ads": Ad.objects.filter(placement=placement, is_active=True)}


@register.filter
def emo_name(key):
    return EMOTION_NAME.get(key, "")


@register.filter
def emo_char(key):
    return EMOTION_CHAR.get(key, "")


@register.filter
def kind_name(key):
    return KIND_NAME.get(key, "")


@register.filter
def mood_word(value):
    try:
        return MOOD_WORDS[int(value)]
    except (TypeError, ValueError, IndexError):
        return ""


@register.filter
def signed(value, digits=0):
    """+4 / −2 / ±0 の形にする。digits を指定すると小数点以下を出す。"""
    if value is None:
        return ""
    v = float(value)
    mark = "+" if v > 0 else "−" if v < 0 else "±"
    body = f"{abs(v):.{int(digits)}f}"
    return mark + body


@register.filter
def trend(value):
    """CSSクラス用：up / down / flat"""
    if value is None:
        return ""
    return "up" if value > 0 else "down" if value < 0 else "flat"
