from ..models import Module, ModuleCompletion

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











