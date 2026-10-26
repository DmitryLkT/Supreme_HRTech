from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import AnswerSubmission, Module, ModuleCompletion
from .permissions import hr_required


def employees_queryset():
    return get_user_model().objects.filter(
        is_active=True, is_superuser=False, is_staff=False,
    ).exclude(groups__name="HR")


@hr_required
@require_GET
def hr_dashboard(request):
    total_modules = Module.objects.filter(is_published=True).count()
    published = Q(modulecompletion__module__is_published=True)
    employees = employees_queryset().annotate(
        completed_count=Count("modulecompletion__module_id", filter=published, distinct=True),
        last_completed_at=Max("modulecompletion__completed_at", filter=published),
    )
    employee_count = employees.count()
    finished_count = employees.filter(completed_count=total_modules).count() if total_modules else 0
    in_progress_count = employees.filter(
        completed_count__gt=0, completed_count__lt=total_modules,
    ).count()

    query = request.GET.get("q", "").strip()[:100]
    if query:
        for word in query.split():
            employees = employees.filter(
                Q(username__icontains=word) | Q(first_name__icontains=word)
                | Q(last_name__icontains=word)
            )
    page = Paginator(employees.order_by("last_name", "first_name", "username", "id"), 20).get_page(request.GET.get("page"))
    for employee in page.object_list:
        employee.progress_percent = round(employee.completed_count / total_modules * 100) if total_modules else 0

    return render(request, "onboarding/hr_dashboard.html", {
        "page_obj": page, "query": query,
        "total_modules": total_modules,
        "employee_count": employee_count,
        "finished_count": finished_count,
        "in_progress_count": in_progress_count,
        "not_started_count": employee_count - finished_count - in_progress_count,
    })


@hr_required
@require_GET
def hr_employee_detail(request, user_id):
    employee = get_object_or_404(employees_queryset(), pk=user_id)
    modules = list(Module.objects.filter(is_published=True))
    completions = {
        item.module_id: item.completed_at
        for item in ModuleCompletion.objects.filter(user=employee, module__is_published=True)
    }
    for module in modules:
        module.employee_completed_at = completions.get(module.id)
    total_modules = len(modules)
    completed_count = len(completions)
    submissions = AnswerSubmission.objects.filter(
        user=employee, question__module__is_published=True,
    )
    scored = submissions.exclude(is_correct__isnull=True)
    return render(request, "onboarding/hr_employee_detail.html", {
        "employee": employee, "modules": modules,
        "answers_total": submissions.count(),
        "scored_total": scored.count(),
        "scored_correct": scored.filter(is_correct=True).count(),
        "completed_count": completed_count, "total_modules": total_modules,
        "progress_percent": round(completed_count / total_modules * 100) if total_modules else 0,
    })


@hr_required
@require_GET
def hr_answers(request):
    """Сводка ответов на вопросы модулей. Только агрегаты, без имён."""
    modules = list(Module.objects.filter(is_published=True))
    selected = None
    raw = request.GET.get("module", "")
    if raw.isdecimal():
        selected = next((m for m in modules if m.id == int(raw)), None)

    employee_ids = employees_queryset().values("id")
    counts = {
        row["option_id"]: row["n"]
        for row in AnswerSubmission.objects
        .filter(user_id__in=employee_ids, question__module__is_published=True)
        .values("option_id").annotate(n=Count("id"))
    }

    blocks = []
    for module in (modules if selected is None else [selected]):
        questions = []
        for question in module.questions.prefetch_related("options"):
            options = list(question.options.all())
            total = sum(counts.get(o.id, 0) for o in options)
            scored = question.is_scored
            rows = []
            for option in options:
                n = counts.get(option.id, 0)
                rows.append({
                    "text": option.text, "count": n,
                    "percent": round(n / total * 100) if total else 0,
                    "is_correct": option.is_correct if scored else None,
                })
            correct_n = sum(r["count"] for r in rows if r["is_correct"])
            questions.append({
                "text": question.text, "scored": scored, "total": total,
                "rows": rows,
                "correct_percent": round(correct_n / total * 100) if scored and total else None,
            })
        blocks.append({"module": module, "questions": questions})

    return render(request, "onboarding/hr_answers.html", {
        "modules": modules, "selected": selected, "blocks": blocks,
        "employees_total": employees_queryset().count(),
    })
