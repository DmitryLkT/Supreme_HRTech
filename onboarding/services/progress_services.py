from django.db.models import Count

from ..models import Module, ModuleCompletion, AnswerSubmission
from onboarding.services.employee_services import employees_queryset

def get_user_module_progress(user):
    """Собирает данные для главной страницы и рассчитывает прогресс"""
    modules = list(Module.objects.filter(is_published=True).order_by("order", "id"))
    completed_module_ids = set(
        ModuleCompletion.objects.filter(
            user=user, module__is_published=True,
        ).values_list("module_id", flat=True)
    )
    total_modules = len(modules)
    completed_count = len(completed_module_ids)
    progress_percent = round(completed_count / total_modules * 100) if total_modules else 0
    next_module = next(
        (module for module in modules if module.pk not in completed_module_ids),
        None,
    )

    return {
        "page_title": "Твой маршрут адаптации",
        "modules": modules,
        "completed_module_ids": completed_module_ids,
        "total_modules": total_modules,
        "completed_count": completed_count,
        "progress_percent": progress_percent,
        "next_module": next_module,
    }

def get_last_answer_progress(user):
    return AnswerSubmission.objects.filter(
        user=user, question__module__is_published=True,
    )

def get_answers_count_by_options(module) -> dict[int, int]:
    """Количество ответов сотрудников по каждому варианту: {option_id: количество}."""
    filters = {
        "user_id__in": employees_queryset().values("id"),
        "question__module__is_published": True,
    }
    if module is not None:
        filters["question__module_id"] = module.id
    return dict(
        AnswerSubmission.objects
        .filter(**filters)
        .values_list("option_id")
        .annotate(n=Count("id"))
    )









