from django.shortcuts import get_object_or_404

from ..models import Question, AnswerOption

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
    correct_option = _get_correct_option(question)
    is_correct = selected_option.is_correct

    if is_correct:
        message = "Правильно!"
    else:
        message = "Неверно. Попробуй ещё раз."
        if correct_option:
            message += f" Правильный ответ: {correct_option.text}"

    return {
        "question": question,
        "correct_option": correct_option,
        "is_correct": is_correct,
        "message": message
    }

def _get_correct_option(question):
    """Получение правильного варианта"""
    return question.options.filter(is_correct=True).first()