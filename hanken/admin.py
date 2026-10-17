from django.contrib import admin

from .models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "user", "before_emo", "before_mood", "after_emo", "after_mood", "share", "created_at")
    list_filter = ("kind", "share", "before_emo", "after_emo")
    search_fields = ("title", "user__username")
    date_hierarchy = "created_at"
