from django.db import IntegrityError
from django.utils import timezone
from django.shortcuts import get_object_or_404

from ..models import PathStep, PathProgress, MentorQuestion

def get_list_path_step():
    """Возвращает шаги из плана «Первые 90 дней»"""
    return PathStep.objects.filter(is_published=True)

def get_done_ids(*, request, steps):
    """Возвращает id выполненного шага"""
    return set(
        PathProgress.objects.filter(user=request.user, step__in=steps)
        .values_list("step_id", flat=True)
    )

def get_periods_from_path_steps(*, PERIOD_DESCRIPTIONS, steps, done_ids, now_period):
    """Собирает по периодам шаги пути: отмечает выполненные и текущий период."""
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
    return periods

def get_published_path_step(step_id):
    """Возвращает опубликованный шаг пути по id"""
    return get_object_or_404(PathStep, step_id=step_id, is_published=True)

def toggle_path_step_progress(*, user, step):
    """Отмечает шаг выполненным или снимает отметку"""
    deleted, _ = PathProgress.objects.filter(user=user, step=step).delete()
    if not deleted:
        try:
            PathProgress.objects.create(user=user, step=step)
        except IntegrityError:
            pass  # параллельный запрос уже создал запись

def get_mentor_question(question_id):
    """Возвращает вопрос наставнику по id"""
    return get_object_or_404(MentorQuestion, id=question_id)

def save_mentor_answer(*, question, answer, user):
    """Записывает ответ на вопрос наставнику с автором и временем"""
    if not answer:
        return
    question.answer = answer
    question.answered_by = user
    question.answered_at = timezone.now()
    question.save(update_fields=["answer", "answered_by", "answered_at"])