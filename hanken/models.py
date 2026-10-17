import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .emotions import EMOTION_CHOICES, KIND_CHOICES, SHARE_CHOICES


def photo_path(instance, filename):
    # 推測されにくいファイル名にする（元のファイル名は使わない）
    return f"photos/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.jpg"


MOOD = [MinValueValidator(1), MaxValueValidator(10)]


class Entry(models.Model):
    """1枚の半券。左半分が観る前、右半分が観た後。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="entries", verbose_name="記録した人")
    kind = models.CharField("種類", max_length=10, choices=KIND_CHOICES, default="book")
    title = models.CharField("作品名", max_length=80)
    share = models.CharField("共有", max_length=10, choices=SHARE_CHOICES, default="public")
    created_at = models.DateTimeField("作成日時", auto_now_add=True)

    before_emo = models.CharField("観る前の気持ち", max_length=12, choices=EMOTION_CHOICES)
    before_mood = models.PositiveSmallIntegerField("観る前の気分", validators=MOOD)
    before_note = models.TextField("観る前のひとこと", max_length=300, blank=True)
    before_photo = models.ImageField("観る前の写真", upload_to=photo_path, blank=True)
    before_at = models.DateTimeField("観る前の記録日時", default=timezone.now)

    after_emo = models.CharField("観た後の気持ち", max_length=12, choices=EMOTION_CHOICES, blank=True)
    after_mood = models.PositiveSmallIntegerField("観た後の気分", validators=MOOD, null=True, blank=True)
    after_note = models.TextField("観た後のひとこと", max_length=300, blank=True)
    after_photo = models.ImageField("観た後の写真", upload_to=photo_path, blank=True)
    after_at = models.DateTimeField("観た後の記録日時", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "半券"
        verbose_name_plural = "半券"
        indexes = [models.Index(fields=["share", "before_emo"])]

    def __str__(self):
        return f"{self.title}（{self.get_kind_display()}）"

    @property
    def is_done(self):
        return bool(self.after_emo) and self.after_mood is not None

    @property
    def delta(self):
        if not self.is_done:
            return None
        return self.after_mood - self.before_mood

    @property
    def is_shared(self):
        return self.share != "private"

    def delete_photos(self):
        for f in (self.before_photo, self.after_photo):
            if f:
                f.delete(save=False)
