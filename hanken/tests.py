from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from . import analysis
from .models import Ad, Entry, Work

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

    def test_recent_works_lists_ten_newest_per_kind(self):
        now = timezone.now()
        for kind in ("movie", "book", "drama"):
            for i in range(12):
                w = Work.objects.create(kind=kind, title=f"{kind}-{i:02d}")
                Work.objects.filter(pk=w.pk).update(updated_at=now - timezone.timedelta(days=i))
        r = self.client.get(reverse("hanken:recent"))
        sections = r.context["sections"]
        self.assertEqual([s["kind"] for s in sections], ["movie", "book", "drama"])
        for s in sections:
            titles = [w.title for w in s["works"]]
            self.assertEqual(titles, [f"{s['kind']}-{i:02d}" for i in range(10)])
        self.assertNotContains(r, 'http-equiv="refresh"')

    def test_recent_works_link(self):
        Work.objects.create(kind="movie", title="リンクあり", url="https://example.com/movie")
        Work.objects.create(kind="movie", title="リンクなし")
        r = self.client.get(reverse("hanken:recent"))
        self.assertContains(r, '<a class="work-in" href="https://example.com/movie" target="_blank" rel="noopener noreferrer">')
        self.assertContains(r, 'リンクあり<span class="ext"')
        self.assertContains(r, '<span class="work-title">リンクなし</span>')
        with self.assertRaises(ValidationError):
            Work(kind="book", title="危険", url="javascript:alert(1)").full_clean()

    def test_work_image_upload_from_admin(self):
        User.objects.filter(pk=self.a.pk).update(is_staff=True, is_superuser=True)
        r = self.client.post(reverse("admin:hanken_work_add"),
                             {"kind": "book", "title": "画像つき", "note": "", "url": "", "image": png()})
        self.assertEqual(r.status_code, 302)
        w = Work.objects.get(title="画像つき")
        self.assertTrue(w.image.name.startswith("works/book/") and w.image.name.endswith(".jpg"))
        with w.image.open() as f:
            self.assertEqual(max(Image.open(f).size), 800)
        self.assertContains(self.client.get(reverse("hanken:recent")), f'<img src="{w.image.url}"')

        old = w.image.name
        self.client.post(reverse("admin:hanken_work_change", args=[w.pk]),
                         {"kind": "book", "title": "画像つき", "note": "", "url": "", "image": png()})
        w.refresh_from_db()
        self.assertNotEqual(w.image.name, old)
        self.assertFalse(w.image.storage.exists(old))

        self.client.post(reverse("admin:hanken_work_delete", args=[w.pk]), {"post": "yes"})
        self.assertFalse(w.image.storage.exists(w.image.name))

    def test_work_cover_prefers_upload_over_image_url(self):
        ext = "https://example.com/cover.jpg"
        w = Work.objects.create(kind="drama", title="URLだけ", image_url=ext)
        self.assertEqual(w.cover_url, ext)
        r = self.client.get(reverse("hanken:recent"))
        self.assertContains(r, f'<img src="{ext}" alt="" loading="lazy" referrerpolicy="no-referrer">')

        w.image.save("w.jpg", SimpleUploadedFile("w.jpg", png().read()), save=True)
        self.assertEqual(w.cover_url, w.image.url)
        r = self.client.get(reverse("hanken:recent"))
        self.assertContains(r, f'<img src="{w.image.url}"')
        self.assertNotContains(r, ext)
        w.image.delete(save=False)

        self.assertEqual(Work(kind="book", title="なし").cover_url, "")
        with self.assertRaises(ValidationError):
            Work(kind="book", title="危険", image_url="javascript:alert(1)").full_clean()

    def test_new_entry_links_to_matching_work(self):
        ext = "https://example.com/witch.jpg"
        Work.objects.create(kind="movie", title="西の魔女が死んだ", url="https://example.com/movie")
        book = Work.objects.create(kind="book", title="西の魔女が死んだ", url="https://example.com/book", image_url=ext)
        self.client.post(reverse("hanken:record"), {
            "kind": "book", "title": " 西の魔女が死んだ ", "before_emo": "tired", "before_mood": 3, "share": "public"})
        e = Entry.objects.get()
        self.assertEqual(e.work, book)  # 同じ種類の作品が優先される
        r = self.client.get(reverse("hanken:mine"))
        self.assertContains(r, 'href="https://example.com/book" target="_blank" rel="noopener noreferrer">西の魔女が死んだ')
        self.assertContains(r, f'<span class="stub-cover"><img src="{ext}"')

        self.client.post(reverse("hanken:record"), {
            "kind": "drama", "title": "西の魔女が死んだ", "before_emo": "sad", "before_mood": 4, "share": "public"})
        self.assertIsNotNone(Entry.objects.get(kind="drama").work)  # 種類違いでも作品名が同じなら結びつく

        self.client.post(reverse("hanken:record"), {
            "kind": "book", "title": "まだない作品", "before_emo": "sad", "before_mood": 4, "share": "public"})
        self.assertIsNone(Entry.objects.get(title="まだない作品").work)

    def test_work_added_later_links_existing_entries(self):
        e = make(self.a, "Later Work", "sad", 3, "calm", 7, kind="movie")
        User.objects.filter(pk=self.a.pk).update(is_staff=True, is_superuser=True)
        self.client.post(reverse("admin:hanken_work_add"),
                         {"kind": "movie", "title": "later work", "note": "", "url": "", "image_url": ""})
        e.refresh_from_db()
        self.assertEqual(e.work.title, "later work")
        e.work.delete()
        e.refresh_from_db()
        self.assertIsNone(e.work)  # 作品を消しても半券は残る

    def test_ads_render_raw_html_with_pr_label(self):
        tag = ('<a href="https://px.a8.net/svt/ejp?a8mat=X&a8ejpredirect=https%3A%2F%2Fexample.com%2F" rel="nofollow">広告文</a>'
               '<img border="0" width="1" height="1" src="https://www15.a8.net/0.gif?a8mat=X" alt="">')
        Ad.objects.create(name="下の広告", placement="footer", html=tag)
        Ad.objects.create(name="最近の作品の広告", placement="recent", html="<b>recent-ad</b>")
        Ad.objects.create(name="止めた広告", placement="footer", html="<b>off-ad</b>", is_active=False)

        r = self.client.get(reverse("hanken:mine"))
        self.assertContains(r, tag)  # 改変されずにそのまま出る
        self.assertContains(r, '<span class="pr">PR</span>')
        self.assertNotContains(r, "recent-ad")
        self.assertNotContains(r, "off-ad")
        self.assertContains(self.client.get(reverse("hanken:recent")), "<b>recent-ad</b>")

        Ad.objects.all().delete()
        self.assertNotContains(self.client.get(reverse("hanken:mine")), 'class="ads"')

    def test_admin_tab_only_for_staff(self):
        admin_link = f'href="{reverse("admin:index")}">管理画面'
        self.assertNotContains(self.client.get(reverse("hanken:recent")), admin_link)
        User.objects.filter(pk=self.a.pk).update(is_staff=True)
        self.assertContains(self.client.get(reverse("hanken:recent")), admin_link)

    def test_login_goes_to_recent_works(self):
        self.client.logout()
        r = self.client.post(reverse("login"), {"username": "a", "password": "pw-123456-x"})
        self.assertRedirects(r, reverse("hanken:recent"))

    def test_signup(self):
        self.client.logout()
        r = self.client.post(reverse("signup"), {"username": "newbie",
                                                  "password1": "kanjo-hanken-2026", "password2": "kanjo-hanken-2026"})
        self.assertRedirects(r, reverse("hanken:recent"))
