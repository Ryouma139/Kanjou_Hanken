import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from .emotions import EMOTION_CHOICES, KIND_CHOICES, SHARE_CHOICES


def photo_path(instance, filename):
    # 推測されにくいファイル名にする（元のファイル名は使わない）
    return f"photos/{timezone.now():%Y/%m}/{uuid.uuid4().hex}.jpg"


def work_image_path(instance, filename):
    return f"works/{instance.kind}/{uuid.uuid4().hex}.jpg"


MOOD = [MinValueValidator(1), MaxValueValidator(10)]


class Work(models.Model):
    """管理画面で登録する作品。「最近の作品」に更新日時の新しい順で並ぶ。"""

    kind = models.CharField("種類", max_length=10, choices=KIND_CHOICES)
    title = models.CharField("作品名", max_length=80)
    note = models.CharField("ひとこと紹介", max_length=120, blank=True)
    url = models.URLField("リンク", blank=True,
                          help_text="公式サイト、配信ページ、書籍の販売ページなど。空なら作品名はリンクになりません。")
    image = models.ImageField("画像", upload_to=work_image_path, blank=True,
                              help_text="表紙やポスターなど。縦長（2:3）がきれいに収まります。保存時に長辺800pxへ縮小します。")
    image_url = models.URLField("画像URL", max_length=500, blank=True,
                                help_text="ほかのサイトの画像アドレス。上の「画像」をアップロードしている場合は、そちらが優先されます。")
    created_at = models.DateTimeField("登録日時", auto_now_add=True)
    updated_at = models.DateTimeField("更新日時", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "作品"
        verbose_name_plural = "作品"
        constraints = [models.UniqueConstraint(fields=["kind", "title"], name="unique_work_kind_title")]
        indexes = [models.Index(fields=["kind", "-updated_at"])]

    def __str__(self):
        return f"{self.title}（{self.get_kind_display()}）"

    @property
    def cover_url(self):
        """表示する画像のURL。アップロードした画像を優先し、なければ画像URL。どちらもなければ空。"""
        return self.image.url if self.image else self.image_url

    @classmethod
    def match(cls, kind, title):
        """作品名が一致する作品（前後の空白・英字の大小は無視）。同じ種類を優先し、なければ種類違いでも同名のもの。"""
        title = (title or "").strip()
        if not title:
            return None
        same = cls.objects.filter(title__iexact=title)
        return same.filter(kind=kind).first() or same.first()


class Entry(models.Model):
    """1枚の半券。左半分が観る前、右半分が観た後。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="entries", verbose_name="記録した人")
    work = models.ForeignKey(Work, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="entries", verbose_name="作品")
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
    def finished_on(self):
        """観終わった日（日本時間）。観た後が未記録なら None。"""
        if not self.is_done:
            return None
        return timezone.localtime(self.after_at or self.created_at).date()

    @property
    def is_shared(self):
        return self.share != "private"

    def delete_photos(self):
        for f in (self.before_photo, self.after_photo):
            if f:
                f.delete(save=False)
