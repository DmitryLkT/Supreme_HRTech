from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.http import require_GET

from onboarding.permissions import hr_required
from onboarding.services.employee_services import get_employees_queryset, filtering_employees_words, get_employee, add_completion_date_each_module, employees_queryset
from onboarding.services.dashboard_services import calculate_general_statistics, calculate_progress_percentage, calculate_progress_percent, calculate_answers_statistics
from onboarding.services.module_services import get_published_modules, get_completion_dates_modules_employee, get_number_published_modules, get_published_modules_with_questions, get_selected_module
from onboarding.services.progress_services import get_last_answer_progress, get_answers_count_by_options

@hr_required
@require_GET
def hr_dashboard(request):
    """Формирует HR-панель управления обучениея сотрудников"""
    total_modules = get_number_published_modules()

    employees = get_employees_queryset()

    employee_context = calculate_general_statistics(employees=employees, total_modules=total_modules)

    query = request.GET.get("q", "").strip()[:100]
    if query:
        employees = filtering_employees_words(query=query, employees=employees)

    page = Paginator(
        employees.order_by("last_name", "first_name", "username", "id"),
        20
        ).get_page(request.GET.get("page"))

    calculate_progress_percentage(page=page, total_modules=total_modules)

    return render(request, "onboarding/hr_dashboard.html", {
        "page_obj": page, "query": query,
        "total_modules": total_modules,
        "employees_count": employee_context["employees_count"],
        "finished_count": employee_context["finished_count"],
        "in_progress_count": employee_context["in_progress_count"],
        "not_started_count": employee_context["not_started_count"]
    })


@hr_required
@require_GET
def hr_employee_detail(request, user_id):
    """Формирует страницу HR с подробной информацией об обучении конкретного сотрудника"""
    employee = get_employee(user_id)

    modules = get_published_modules()

    completions = get_completion_dates_modules_employee(employee)

    add_completion_date_each_module(modules=modules, completions=completions)

    total_modules = len(modules)
    completed_count = len(completions)

    submissions = get_last_answer_progress(employee)
    scored = submissions.exclude(is_correct__isnull=True)

    progress_percent = calculate_progress_percent(completed_count=completed_count, total_modules=total_modules)

    return render(request, "onboarding/hr_employee_detail.html", {
        "employee": employee,
        "answers_total": submissions.count(),
        "scored_total": scored.count(),
        "scored_correct": scored.filter(is_correct=True).count(),
        "modules": modules,
        "completed_count": completed_count,
        "total_modules": total_modules,
        "progress_percent": progress_percent
    })

@hr_required
@require_GET
def hr_answers(request):
    """Сводка ответов на вопросы модулей. Только агрегаты, без имён."""
    modules = get_published_modules_with_questions

    selected = get_selected_module(modules=modules, raw=request.GET.get("module", ""))

    counts = get_answers_count_by_options(module=selected)

    modules_for_statistics = [selected] if selected is not None else modules

    blocks = calculate_answers_statistics(modules=modules_for_statistics, counts=counts)

    return render(request, "onboarding/hr_answers.html", {
        "modules": modules,
        "selected": selected,
        "blocks": blocks,
        "employees_total": employees_queryset().count(),
    })
