from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps

from .emotions import EMOTION_CHOICES, KIND_CHOICES, SHARE_CHOICES
from .models import Entry


class RangeInput(forms.NumberInput):
    input_type = "range"


def shrink_photo(upload):
    """向きを補正し、長辺を縮めたJPEGにする。"""
    if not upload:
        return None
    side = getattr(settings, "HANKEN_PHOTO_MAX_SIDE", 1280)
    img = Image.open(upload)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((side, side))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return ContentFile(buf.getvalue(), name="photo.jpg")


def emo_field(required, label):
    msg = f"{label}を一つ選んでください。"
    return forms.ChoiceField(label=label, choices=EMOTION_CHOICES, required=required,
                             widget=forms.RadioSelect, error_messages={"required": msg})


def mood_field(required=True):
    return forms.IntegerField(label="気分", min_value=1, max_value=10, initial=5, required=required,
                              widget=RangeInput(attrs={"min": 1, "max": 10, "step": 1}))


def photo_field():
    return forms.ImageField(label="写真", required=False,
                            widget=forms.FileInput(attrs={"accept": "image/*"}))


def note_field(placeholder):
    return forms.CharField(label="ひとこと", max_length=300, required=False,
                           widget=forms.Textarea(attrs={"rows": 3, "placeholder": placeholder}))


class PhotoSizeMixin:
    def _check_photo(self, name):
        f = self.cleaned_data.get(name)
        limit = getattr(settings, "HANKEN_PHOTO_MAX_BYTES", 10 * 1024 * 1024)
        if f and f.size > limit:
            raise forms.ValidationError("写真が大きすぎます。10MB以下の画像を選んでください。")
        return f

    def clean_before_photo(self):
        return self._check_photo("before_photo")

    def clean_after_photo(self):
        return self._check_photo("after_photo")


class PhaseMixin:
    """テンプレートで観る前／観た後のブロックを同じ部品で描くための束ね。"""

    def _phase(self, prefix, title, eyebrow):
        return {
            "key": prefix,
            "title": title,
            "eyebrow": eyebrow,
            "emo": self[f"{prefix}_emo"],
            "mood": self[f"{prefix}_mood"],
            "photo": self[f"{prefix}_photo"],
            "note": self[f"{prefix}_note"],
        }

    @property
    def after_phase(self):
        return self._phase("after", "観た後の気持ち", "After")


class RecordForm(PhotoSizeMixin, PhaseMixin, forms.Form):
    kind = forms.ChoiceField(label="種類", choices=KIND_CHOICES, initial="book", widget=forms.RadioSelect)
    title = forms.CharField(label="作品名", max_length=80,
                            widget=forms.TextInput(attrs={"placeholder": "例：西の魔女が死んだ", "autocomplete": "off"}),
                            error_messages={"required": "作品名を入力してください。"})

    before_emo = emo_field(True, "観る前の気持ち")
    before_mood = mood_field()
    before_photo = photo_field()
    before_note = note_field("例：仕事で失敗して、頭が重い。")

    both = forms.BooleanField(label="もう観終わった（観た後の気持ちも一緒に記録する）", required=False)

    after_emo = emo_field(False, "観た後の気持ち")
    after_mood = mood_field(required=False)
    after_photo = photo_field()
    after_note = note_field("例：主人公の言葉に救われた。少し泣いた。")

    share = forms.ChoiceField(label="共有のしかた", choices=SHARE_CHOICES, initial="public", widget=forms.RadioSelect)

    @property
    def before_phase(self):
        return self._phase("before", "観る前の気持ち", "Before")

    def clean(self):
        data = super().clean()
        if data.get("both"):
            if not data.get("after_emo"):
                self.add_error("after_emo", "観た後の気持ちも一つ選んでください。")
            if not data.get("after_mood"):
                self.add_error("after_mood", "観た後の気分を選んでください。")
        return data

    def save(self, user):
        d = self.cleaned_data
        now = timezone.now()
        entry = Entry(user=user, kind=d["kind"], title=d["title"].strip(), share=d["share"],
                      before_emo=d["before_emo"], before_mood=d["before_mood"],
                      before_note=d.get("before_note", ""), before_at=now)
        if d.get("before_photo"):
            entry.before_photo.save("photo.jpg", shrink_photo(d["before_photo"]), save=False)
        if d.get("both"):
            entry.after_emo = d["after_emo"]
            entry.after_mood = d["after_mood"]
            entry.after_note = d.get("after_note", "")
            entry.after_at = now
            if d.get("after_photo"):
                entry.after_photo.save("photo.jpg", shrink_photo(d["after_photo"]), save=False)
        entry.save()
        return entry


class AfterForm(PhotoSizeMixin, PhaseMixin, forms.Form):
    after_emo = emo_field(True, "観た後の気持ち")
    after_mood = mood_field()
    after_photo = photo_field()
    after_note = note_field("例：主人公の言葉に救われた。少し泣いた。")

    def save(self, entry):
        d = self.cleaned_data
        entry.after_emo = d["after_emo"]
        entry.after_mood = d["after_mood"]
        entry.after_note = d.get("after_note", "")
        entry.after_at = timezone.now()
        if d.get("after_photo"):
            if entry.after_photo:
                entry.after_photo.delete(save=False)
            entry.after_photo.save("photo.jpg", shrink_photo(d["after_photo"]), save=False)
        entry.save()
        return entry


class ShareForm(forms.Form):
    share = forms.ChoiceField(choices=SHARE_CHOICES)


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)
        labels = {"username": "ニックネーム（ログインID）"}
