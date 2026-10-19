from datetime import date, timedelta

from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from onboarding.hr_views import employees_queryset
from onboarding.permissions import employee_required, hr_required

from .models import AnswerUser, Questionnaire, QuestionnaireCompletion
from .scoring import category_scores, completion_pairs

COMMENT_MAX_LENGTH = 1000
HR_PAGE_SIZE = 20


def current_week_start():
    """Понедельник текущей недели."""
    today = timezone.localdate()
    return today - timedelta(days=today.weekday())


@employee_required
@require_http_methods(["GET", "POST"])
def questionnaire(request):
    if request.user.is_superuser:
        return redirect("hr_health")

    active = Questionnaire.objects.filter(status=Questionnaire.Status.ACTIVE).first()
    week_start = current_week_start()
    context = {"week_start": week_start, "questionnaire": active}

    if active is None:
        context["state"] = "no_active"
        return render(request, "health/form.html", context)

    completion = QuestionnaireCompletion.objects.filter(
        user=request.user, week_start=week_start,
    ).first()
    if completion:
        context.update(state="done", completion=completion)
        return render(request, "health/form.html", context)

    questions = list(
        active.questionquestionnaire_set.prefetch_related("answeroption_set")
    )
    for question in questions:
        question.options = list(question.answeroption_set.all())
        question.selected_id = None
    context.update(state="form", questions=questions, comment="", errors=[])

    if request.method == "GET":
        return render(request, "health/form.html", context)

    # ---- POST ----
    selected, chosen, errors = {}, [], []
    for question in questions:
        raw = request.POST.get(f"q_{question.id}", "")
        option = next((o for o in question.options if str(o.id) == raw), None)
        if option:
            selected[question.id] = option.id
            chosen.append((question, option))
        elif question.is_required:
            errors.append(f"Ответь на вопрос {questions.index(question) + 1}.")

    comment = request.POST.get("comment", "").strip()[:COMMENT_MAX_LENGTH]
    if not active.comment_prompt:
        comment = ""

    if errors:
        for question in questions:
            question.selected_id = selected.get(question.id)
        context.update(comment=comment, errors=errors)
        return render(request, "health/form.html", context, status=400)

    try:
        with transaction.atomic():
            completion = QuestionnaireCompletion.objects.create(
                user=request.user, questionnaire=active,
                week_start=week_start, comment=comment,
            )
            AnswerUser.objects.bulk_create([
                AnswerUser(
                    questionnaire_completion=completion,
                    question_questionnaire=question,
                    answer_option=option,
                )
                for question, option in chosen
            ])
    except IntegrityError:
        pass  # анкета на этой неделе уже отправлена (например, двойной клик)
    return redirect("health_form")


@hr_required
@require_GET
def hr_health(request):
    weeks = list(
        QuestionnaireCompletion.objects.order_by("-week_start")
        .values_list("week_start", flat=True).distinct()
    )
    week = None
    raw_week = request.GET.get("week", "")
    try:
        requested = date.fromisoformat(raw_week) if raw_week else None
    except ValueError:
        requested = None
    if requested in weeks:
        week = requested
    elif weeks:
        week = weeks[0]

    employees_total = employees_queryset().count()
    rows, overall = [], []

    if week:
        completions = (
            QuestionnaireCompletion.objects
            .filter(week_start=week, user__in=employees_queryset())
            .select_related("user")
            .prefetch_related(Prefetch(
                "answeruser_set",
                queryset=AnswerUser.objects.select_related(
                    "question_questionnaire", "answer_option",
                ),
            ))
        )
        all_pairs = []
        for completion in completions:
            pairs = completion_pairs(completion)
            all_pairs.extend(pairs)
            scores = category_scores(pairs)
            rows.append({
                "user": completion.user,
                "comment": completion.comment,
                "completed_at": completion.completed_at,
                "scores": scores,
                "top": max((s["average"] for s in scores), default=0),
            })
        # сначала самые высокие значения — им нужно внимание в первую очередь
        rows.sort(key=lambda r: (-r["top"], r["user"].get_username()))
        overall = category_scores(all_pairs)
        keys = [item["key"] for item in overall]
        for row in rows:
            by_key = {item["key"]: item for item in row["scores"]}
            row["cells"] = [by_key.get(key) for key in keys]  # столбцы строго по порядку заголовков

    page = Paginator(rows, HR_PAGE_SIZE).get_page(request.GET.get("page"))

    return render(request, "health/hr_health.html", {
        "weeks": weeks,
        "week": week,
        "page_obj": page,
        "respondents": len(rows),
        "employees_total": employees_total,
        "overall": overall,
    })
