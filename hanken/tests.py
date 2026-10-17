from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from . import analysis
from .models import Entry

User = get_user_model()


def make(user, title, before, bm, after=None, am=None, share="public", kind="movie"):
    return Entry.objects.create(user=user, title=title, kind=kind, share=share,
                                before_emo=before, before_mood=bm,
                                after_emo=after or "", after_mood=am)


def png():
    buf = BytesIO()
    Image.new("RGB", (2000, 1000), (120, 140, 200)).save(buf, "PNG")
    return SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")


class AnalysisTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", password="pw-123456-x")

    def test_summary_and_ranking(self):
        es = [make(self.a, "X", "anxious", 3, "calm", 7),
              make(self.a, "x ", "anxious", 4, "calm", 6),
              make(self.a, "Y", "anxious", 5, "sad", 4)]
        s = analysis.summarize(es)
        self.assertEqual(s["n"], 3)
        self.assertAlmostEqual(s["avg"], (4 + 2 - 1) / 3)
        self.assertEqual(s["up_pct"], 67)
        rank = analysis.work_ranking(es)
        self.assertEqual(rank[0]["n"], 2)  # X と x は同じ作品
        self.assertEqual(rank[0]["avg"], 3)

    def test_open_entries_are_ignored(self):
        es = [make(self.a, "Z", "tired", 3)]
        self.assertEqual(analysis.summarize(es)["n"], 0)
        self.assertEqual(analysis.slope_chart(es)["lines"], [])


@override_settings(MEDIA_ROOT="/tmp/hanken-test-media")
class ViewTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", password="pw-123456-x")
        self.b = User.objects.create_user("b", password="pw-123456-x")
        self.client.login(username="a", password="pw-123456-x")

    def test_login_required(self):
        self.client.logout()
        r = self.client.get(reverse("hanken:mine"))
        self.assertEqual(r.status_code, 302)

    def test_record_before_then_after(self):
        r = self.client.post(reverse("hanken:record"), {
            "kind": "book", "title": "西の魔女が死んだ", "before_emo": "tired",
            "before_mood": 3, "share": "anon", "before_photo": png()})
        self.assertRedirects(r, reverse("hanken:record"))
        e = Entry.objects.get()
        self.assertFalse(e.is_done)
        self.assertTrue(e.before_photo.name.endswith(".jpg"))
        with e.before_photo.open() as f:
            self.assertEqual(max(Image.open(f).size), 1280)

        r = self.client.post(reverse("hanken:after", args=[e.pk]),
                             {"after_emo": "calm", "after_mood": 8})
        self.assertRedirects(r, reverse("hanken:reflect", args=[e.pk]))
        e.refresh_from_db()
        self.assertEqual(e.delta, 5)
        r = self.client.get(reverse("hanken:reflect", args=[e.pk]))
        self.assertContains(r, "+5")
        e.delete_photos()

    def test_both_requires_after_emotion(self):
        r = self.client.post(reverse("hanken:record"), {
            "kind": "movie", "title": "T", "before_emo": "sad", "before_mood": 4,
            "both": "on", "after_mood": 6, "share": "public"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "観た後の気持ちも一つ選んでください。")
        self.assertEqual(Entry.objects.count(), 0)

    def test_share_page_hides_private_and_anonymizes(self):
        make(self.b, "公開作品", "anxious", 3, "calm", 7, share="public")
        make(self.b, "匿名作品", "anxious", 3, "joy", 8, share="anon")
        make(self.b, "秘密作品", "anxious", 3, "joy", 9, share="private")
        r = self.client.get(reverse("hanken:share") + "?emo=anxious")
        self.assertContains(r, "公開作品")
        self.assertContains(r, "匿名さん")
        self.assertNotContains(r, "秘密作品")
        self.assertEqual(r.context["stats"]["n"], 2)

    def test_cannot_touch_others_entries(self):
        e = make(self.b, "B", "sad", 3)
        self.assertEqual(self.client.post(reverse("hanken:delete", args=[e.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("hanken:after", args=[e.pk])).status_code, 404)

    def test_mine_page_and_delete(self):
        e = make(self.a, "M", "sad", 3, "calm", 7)
        make(self.a, "N", "tired", 4)
        r = self.client.get(reverse("hanken:mine"))
        self.assertContains(r, "心のお守り作品")
        self.assertContains(r, "鑑賞中")
        r = self.client.post(reverse("hanken:change_share", args=[e.pk]), {"share": "private"})
        e.refresh_from_db()
        self.assertEqual(e.share, "private")
        self.client.post(reverse("hanken:delete", args=[e.pk]))
        self.assertFalse(Entry.objects.filter(pk=e.pk).exists())

    def test_calendar_counts_finished_stubs(self):
        today = timezone.localdate()
        make(self.a, "前後そろい", "sad", 3, "calm", 7)
        make(self.a, "前後そろい2", "tired", 4, "joy", 8)
        make(self.a, "鑑賞中", "tired", 4)
        make(self.b, "他人の", "sad", 3, "calm", 7)
        r = self.client.get(reverse("hanken:calendar"))
        self.assertEqual(r.context["cal"]["total"], 2)
        self.assertEqual(r.context["cal"]["days"], 1)
        cell = next(c for w in r.context["cal"]["weeks"] for c in w if c["in_month"] and c["day"] == today.day)
        self.assertEqual(cell["n"], 2)

        r = self.client.get(reverse("hanken:calendar"), {"m": f"{today:%Y-%m}", "d": today.day})
        self.assertContains(r, "前後そろい2")
        self.assertNotContains(r, "鑑賞中</h3>")
        self.assertNotContains(r, "他人の")

    def test_calendar_ignores_bad_params(self):
        for q in ({"m": "2026-13"}, {"m": "abc"}, {"m": "2026-02", "d": "31"}, {"d": "x"}):
            self.assertEqual(self.client.get(reverse("hanken:calendar"), q).status_code, 200)

    def test_signup(self):
        self.client.logout()
        r = self.client.post(reverse("signup"), {"username": "newbie",
                                                  "password1": "kanjo-hanken-2026", "password2": "kanjo-hanken-2026"})
        self.assertRedirects(r, reverse("hanken:record"))
