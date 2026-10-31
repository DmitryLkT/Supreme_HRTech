from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from health.models import Submission, Answer
from health.services.periods import get_week_start, get_expiration_date

WEEKLY_ALREADY_SUBMITTED = "Вы уже проходили эту анкету на этой неделе"


def create_submission(*, employee, version, department, answers):
    """Сохраняет прохождение анкеты за текущую неделю"""
    questionnaire = version.questionnaire

    if not questionnaire.is_published:
        raise ValidationError("Анкета недоступна для прохождения")

    _validate_answers(definition=version.definition, answers=answers)

    today = timezone.localdate()
    week_start = get_week_start(today)

    if _is_submitted_this_week(
            employee=employee, questionnaire=questionnaire, week_start=week_start):
        raise ValidationError(WEEKLY_ALREADY_SUBMITTED)

    try:
        with transaction.atomic():
            submission = Submission.objects.create(
                employee=employee,
                questionnaire=questionnaire,
                version_quest=version,
                department=department,
                week_start=week_start,
                evaluated_week_start=week_start - timedelta(weeks=1),
                expires_at=get_expiration_date(today),
            )
            Answer.objects.bulk_create([
                Answer(submission=submission, question_code=question_code, value=value)
                for question_code, value in answers.items()
            ])
    except IntegrityError:
        if _is_submitted_this_week(
                employee=employee, questionnaire=questionnaire, week_start=week_start):
            raise ValidationError(WEEKLY_ALREADY_SUBMITTED) from None
        raise

    return submission


def _is_submitted_this_week(*, employee, questionnaire, week_start):
    """Проверяет, есть ли прохождение анкеты сотрудником за указанную неделю"""
    return Submission.objects.filter(
        employee=employee,
        questionnaire=questionnaire,
        week_start=week_start,
    ).exists()

def _validate_answers(*, definition, answers):
    """Проверяет корректность ответов относительно определения анкеты"""
    allowed_values = _get_allowed_values(definition=definition)

    if set(allowed_values) - set(answers):
        raise ValidationError("Нужно ответить на все вопросы")
    if set(answers) - set(allowed_values):
        raise ValidationError("Переданы не известные вопросы")

    for question_code, value in answers.items():
        if type(value) is not int or value not in allowed_values[question_code]:
            raise ValidationError("Недопустимая оценка")


def _get_allowed_values(*, definition):
    """Строит карту допустимых оценок по кодам вопросов"""
    allowed_values = {}
    for category in definition["categories"]:
        for question in category["questions"]:
            allowed_values[question["code"]] = {
                option["value"] for option in question["answers"]
            }
    return allowed_values