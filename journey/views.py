from django.db import IntegrityError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from onboarding.hr_views import employees_queryset
from onboarding.permissions import employee_required, hr_required

from .models import MentorQuestion, PathProgress, PathStep

QUESTION_MAX_LENGTH = 1000
ANSWER_MAX_LENGTH = 2000
PERIOD_DESCRIPTIONS = {
    30: "Освоиться: понять роль, людей и процессы.",
    60: "Работать самостоятельно в знакомых задачах.",
    90: "Отвечать за результат и подвести итоги испытательного срока.",
}


def day_of_path(user):
    """Номер дня с даты создания аккаунта; от 1 до 90."""
    joined = timezone.localtime(user.date_joined).date()
    days = (timezone.localdate() - joined).days + 1
    return max(1, min(days, 90))


def current_period(day):
    return 30 if day <= 30 else 60 if day <= 60 else 90


@employee_required
@require_GET
def path(request):
    if request.user.is_superuser:
        return redirect("hr_path")
    steps = list(PathStep.objects.filter(is_published=True))
    done_ids = set(
        PathProgress.objects.filter(user=request.user, step__in=steps)
        .values_list("step_id", flat=True)
    )
    day = day_of_path(request.user)
    now_period = current_period(day)
    periods = []
    for value, label in PathStep.Period.choices:
        items = [s for s in steps if s.period == value]
        for item in items:
            item.done = item.id in done_ids
        periods.append({
            "value": value, "label": label, "description": PERIOD_DESCRIPTIONS[value],
            "steps": items, "is_now": value == now_period,
            "done": sum(1 for s in items if s.done),
        })
    return render(request, "journey/path.html", {
        "periods": periods, "day": day, "day_percent": round(day / 90 * 100),
        "has_steps": bool(steps),
        "has_placeholder": any(s.is_placeholder for s in steps),
        "done_total": len(done_ids), "steps_total": len(steps),
    })


@employee_required
@require_POST
def toggle_step(request, step_id):
    if request.user.is_superuser:
        return redirect("hr_path")
    step = get_object_or_404(PathStep, id=step_id, is_published=True)
    deleted, _ = PathProgress.objects.filter(user=request.user, step=step).delete()
    if not deleted:
        try:
            PathProgress.objects.create(user=request.user, step=step)
        except IntegrityError:
            pass
    return redirect("path")


@hr_required
@require_GET
def hr_path(request):
    employees = employees_queryset()
    total = employees.count()
    steps = PathStep.objects.filter(is_published=True).annotate(
        done_count=Count("progress", filter=Q(progress__user__in=employees)),
    )
    rows = [{
        "step": s, "done": s.done_count,
        "percent": round(s.done_count / total * 100) if total else 0,
    } for s in steps]
    return render(request, "journey/hr_path.html", {"rows": rows, "employees_total": total})


@employee_required
@require_http_methods(["GET", "POST"])
def mentor(request):
    if request.user.is_superuser:
        return redirect("hr_mentor")
    error = ""
    text = ""
    category = MentorQuestion.Category.TASK
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        raw_category = request.POST.get("category", "")
        category = raw_category if raw_category in MentorQuestion.Category.values else MentorQuestion.Category.OTHER
        if not text:
            error = "Напиши вопрос."
        elif len(text) > QUESTION_MAX_LENGTH:
            error = f"Вопрос длиннее {QUESTION_MAX_LENGTH} символов. Сократи его."
        else:
            MentorQuestion.objects.create(user=request.user, category=category, text=text)
            return redirect("mentor")
    questions = MentorQuestion.objects.filter(user=request.user)
    return render(request, "journey/mentor.html", {
        "questions": questions, "categories": MentorQuestion.Category.choices,
        "error": error, "text": text, "category": category,
        "max_length": QUESTION_MAX_LENGTH,
    }, status=400 if error else 200)


@hr_required
@require_GET
def hr_mentor(request):
    show = request.GET.get("show", "open")
    questions = MentorQuestion.objects.select_related("user")
    if show != "all":
        show = "open"
        questions = questions.filter(answer="")
    open_count = MentorQuestion.objects.filter(answer="").count()
    return render(request, "journey/hr_mentor.html", {
        "questions": questions[:100], "show": show, "open_count": open_count,
        "max_length": ANSWER_MAX_LENGTH,
    })


@hr_required
@require_POST
def hr_mentor_answer(request, question_id):
    question = get_object_or_404(MentorQuestion, id=question_id)
    answer = request.POST.get("answer", "").strip()[:ANSWER_MAX_LENGTH]
    if answer:
        question.answer = answer
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save(update_fields=["answer", "answered_by", "answered_at"])
    return redirect("hr_mentor")
