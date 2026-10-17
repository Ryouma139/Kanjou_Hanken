from django.urls import path

from . import views

app_name = "hanken"

urlpatterns = [
    path("", views.record, name="record"),
    path("mine/", views.mine, name="mine"),
    path("share/", views.share, name="share"),
    path("calendar/", views.calendar, name="calendar"),
    path("entry/<int:pk>/after/", views.add_after, name="after"),
    path("entry/<int:pk>/reflect/", views.reflect, name="reflect"),
    path("entry/<int:pk>/share/", views.change_share, name="change_share"),
    path("entry/<int:pk>/delete/", views.delete_entry, name="delete"),
]
