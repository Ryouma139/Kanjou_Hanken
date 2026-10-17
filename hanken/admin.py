from django import forms
from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from .forms import shrink_photo
from .models import Entry, Work


class WorkAdminForm(forms.ModelForm):
    class Meta:
        model = Work
        fields = ("kind", "title", "note", "url", "image", "image_url")

    def clean_image(self):
        f = self.cleaned_data.get("image")
        limit = getattr(settings, "HANKEN_PHOTO_MAX_BYTES", 10 * 1024 * 1024)
        if f and getattr(f, "size", 0) > limit:
            raise forms.ValidationError("画像が大きすぎます。10MB以下の画像を選んでください。")
        return f


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    form = WorkAdminForm
    list_display = ("thumb", "title", "kind", "note", "has_url", "updated_at")
    list_display_links = ("thumb", "title")
    list_filter = ("kind",)
    search_fields = ("title",)
    date_hierarchy = "updated_at"
    fields = ("kind", "title", "note", "url", "image", "image_url", "preview")
    readonly_fields = ("preview",)

    @admin.display(boolean=True, description="リンク")
    def has_url(self, obj):
        return bool(obj.url)

    @admin.display(description="画像")
    def thumb(self, obj):
        if not obj.cover_url:
            return "—"
        return format_html('<img src="{}" alt="" referrerpolicy="no-referrer" style="height:48px;border-radius:4px">',
                           obj.cover_url)

    @admin.display(description="いま表示される画像")
    def preview(self, obj):
        if not obj.cover_url:
            return "なし（種類の色で表示）"
        source = "アップロードした画像" if obj.image else "画像URL"
        return format_html('<img src="{}" alt="" referrerpolicy="no-referrer" style="max-height:240px;border-radius:6px">'
                           '<br><span>{}を表示中</span>', obj.cover_url, source)

    def save_model(self, request, obj, form, change):
        old = Work.objects.get(pk=obj.pk).image if change else None
        if "image" in form.changed_data and obj.image:
            side = getattr(settings, "HANKEN_WORK_IMAGE_MAX_SIDE", 800)
            obj.image.save("work.jpg", shrink_photo(form.cleaned_data["image"], side), save=False)
        super().save_model(request, obj, form, change)
        if old and old.name != obj.image.name:
            old.storage.delete(old.name)
        # まだ作品に結びついていない同名の半券を結びつける
        for e in Entry.objects.filter(work__isnull=True, title__iexact=obj.title.strip()):
            e.work = Work.match(e.kind, e.title)
            e.save(update_fields=["work"])

    def delete_model(self, request, obj):
        obj.image.delete(save=False)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for w in queryset:
            w.image.delete(save=False)
        super().delete_queryset(request, queryset)


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "work", "user", "before_emo", "before_mood", "after_emo", "after_mood", "share", "created_at")
    list_select_related = ("work", "user")
    list_filter = ("kind", "share", "before_emo", "after_emo")
    search_fields = ("title", "user__username")
    date_hierarchy = "created_at"
