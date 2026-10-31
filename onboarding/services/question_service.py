from django.db import transaction
from django.db.models import F

from django.shortcuts import get_object_or_404

from ..models import Question, AnswerOption,  AnswerSubmission

def get_question(question_id):
    """Возвращает вопрос по id"""
    return get_object_or_404(Question, id=question_id, module__is_published=True)

def get_answer_option_question(*, question, option_id):
    """Возвращает ответ на конкретный вопрос"""
    return get_object_or_404(AnswerOption, id=option_id, question=question)

def validate_answer_option_id(option_id):
    """Проверяет ответы на вопрос на наличие не корректных данных"""
    if not option_id or not option_id.isdecimal():
        return "Выбери вариант ответа."
    return None

def check_answer(*, question, selected_option):
    """Проверяет ответ и формирует результат"""
    scored = question.is_scored
    is_correct = selected_option.is_correct if scored else None
    correct_option = _get_correct_option(question=question, scored=scored)
    message = _build_answer_message(
        scored=scored, is_correct=is_correct, correct_option=correct_option,
    )

    return {
        "question": question,
        "selected_option": selected_option,
        "correct_option": correct_option,
        "is_correct": is_correct,
        "scored": scored,
        "message": message,
    }

def save_answer_submission(*, user, question, selected_option, is_correct):
    """Сохраняет ответ сотрудника или обновляет его, увеличивая счётчик попыток"""
    with transaction.atomic():
        submission, created = AnswerSubmission.objects.get_or_create(
            user=user, question=question,
            defaults={"option": selected_option, "is_correct": is_correct},
        )
        if not created:
            AnswerSubmission.objects.filter(pk=submission.pk).update(
                option=selected_option, is_correct=is_correct,
                attempts=F("attempts") + 1,
            )

def _get_correct_option(question):
    """Получение правильного варианта"""
    return question.options.filter(is_correct=True).first()

def _build_answer_message(*, scored, is_correct, correct_option):
    """Формирует сообщение о результате ответа"""
    if not scored:
        return ("Ответ записан. Здесь нет правильного и неправильного: "
                "важно, как ты поступил бы на самом деле.")
    if is_correct:
        return "Правильно!"
    message = "Неверно. Попробуй ещё раз."
    if correct_option:
        message += f" Правильный ответ: {correct_option.text}"
    return message