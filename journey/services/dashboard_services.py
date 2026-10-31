from django.db.models import Count, Q

from ..models import PathStep

def get_steps_with_done_count(*, employees):
    """Возвращает опубликованные шаги пути с количеством выполнивших их сотрудников"""
    return PathStep.objects.filter(is_published=True).annotate(
        done_count=Count("progress", filter=Q(progress__user__in=employees)),
    )


def calculate_steps_progress(*, steps, employees_total):
    """Формирует строки прогресса: шаг, сколько выполнили, процент"""
    rows = []
    for step in steps:
        done = step.done_count
        rows.append({
            "step": step,
            "done": done,
            "percent": calculate_percent(done, employees_total),
        })
    return rows

def calculate_percent(part: int, total: int) -> int:
    """Процент part от total; 0, если total равен нулю."""
    return round(part / total * 100) if total else 0