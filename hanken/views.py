from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import analysis
from .emotions import EMOTION_NAME
from .forms import AfterForm, RecordForm, ShareForm, SignupForm
from .models import Entry


def author_label(entry, viewer):
    if entry.user_id == viewer.id:
        return "あなた（匿名で共有）" if entry.share == "anon" else "あなた"
    if entry.share == "anon":
        return "匿名さん"
    return entry.user.get_full_name() or entry.user.get_username()


@login_required
def record(request):
    if request.method == "POST":
        form = RecordForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(request.user)
            if entry.is_done:
                return redirect("hanken:reflect", pk=entry.pk)
            messages.success(request, "観る前の気持ちを記録しました。観終わったら「わたしの半券」から続きを記録できます。")
            return redirect("hanken:record")
    else:
        form = RecordForm()
    return render(request, "hanken/record.html", {"form": form, "tab": "record"})


@login_required
def add_after(request, pk):
    entry = get_object_or_404(Entry, pk=pk, user=request.user)
    if request.method == "POST":
        form = AfterForm(request.POST, request.FILES)
        if form.is_valid():
            form.save(entry)
            return redirect("hanken:reflect", pk=entry.pk)
    else:
        initial = {"after_emo": entry.after_emo, "after_mood": entry.after_mood or 5,
                   "after_note": entry.after_note} if entry.is_done else None
        form = AfterForm(initial=initial)
    return render(request, "hanken/after.html", {"form": form, "entry": entry, "tab": "record"})


@login_required
def reflect(request, pk):
    entry = get_object_or_404(Entry, pk=pk, user=request.user)
    if not entry.is_done:
        return redirect("hanken:after", pk=entry.pk)
    return render(request, "hanken/reflect.html", {
        "entry": entry, "care": analysis.care_line(entry.delta), "tab": "record",
    })


@login_required
def mine(request):
    entries = list(request.user.entries.all())
    for e in entries:
        e.author = {"private": "自分だけ", "anon": "匿名で共有中"}.get(e.share, "共有中")
    done = [e for e in entries if e.is_done]
    return render(request, "hanken/mine.html", {
        "tab": "mine",
        "entries": entries,
        "open": [e for e in entries if not e.is_done],
        "done": done,
        "stats": analysis.summarize(done),
        "comfort": analysis.comfort_works(done),
        "chart": analysis.slope_chart(done),
        "confirm": request.GET.get("confirm", ""),
    })


@login_required
@require_POST
def change_share(request, pk):
    entry = get_object_or_404(Entry, pk=pk, user=request.user)
    form = ShareForm(request.POST)
    if form.is_valid():
        entry.share = form.cleaned_data["share"]
        entry.save(update_fields=["share"])
        messages.success(request, f"『{entry.title}』の共有を「{entry.get_share_display()}」にしました。")
    return redirect(reverse("hanken:mine") + f"#e{entry.pk}")


@login_required
@require_POST
def delete_entry(request, pk):
    entry = get_object_or_404(Entry, pk=pk, user=request.user)
    title = entry.title
    entry.delete_photos()
    entry.delete()
    messages.success(request, f"『{title}』の半券を削除しました。")
    return redirect("hanken:mine")


@login_required
def share(request):
    pool = list(
        Entry.objects.exclude(share="private").exclude(after_emo="")
        .filter(after_mood__isnull=False).select_related("user")
    )
    ctx = {"tab": "share", "total": len(pool)}
    if not pool:
        return render(request, "hanken/share.html", ctx)

    counts = analysis.before_counts(pool)
    available = {c["key"] for c in counts}
    sel = request.GET.get("emo")
    if sel not in available:
        latest = request.user.entries.filter(before_emo__in=available).first()
        sel = latest.before_emo if latest else max(counts, key=lambda c: c["n"])["key"]

    group = [e for e in pool if e.before_emo == sel]
    recent = sorted(group, key=lambda e: e.after_at or e.created_at, reverse=True)[:6]
    for e in recent:
        e.author = author_label(e, request.user)

    ctx.update({
        "counts": counts,
        "sel": sel,
        "sel_name": EMOTION_NAME[sel],
        "stats": analysis.summarize(group),
        "dist": analysis.after_distribution(group),
        "works": analysis.work_ranking(group),
        "recent": recent,
    })
    return render(request, "hanken/share.html", ctx)


def signup(request):
    if request.user.is_authenticated:
        return redirect("hanken:record")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("hanken:record")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})
