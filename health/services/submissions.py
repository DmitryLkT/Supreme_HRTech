from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction

from ..models import Submission, Answer
from .periods import get_week_start, get_expiration_date

def create_submission(*, employee, version, department, answers):
    """Сохраняет прохождение"""
    questionnaire = version.questionnaire

    if not questionnaire.is_published:
        raise ValidationError("Анкета недоступна для прохождения")
    _validate_answers(definition=version.definition, answers=answers)

    now_datetime = timezone.localdate()
    week_start = get_week_start(now_datetime)

    already_submitted = Submission.objects.filter(
        employee=employee,
        questionnaire=questionnaire,
        week_start=week_start
    ).exists()
    if already_submitted: raise ValidationError("Вы уже проходили эту анкету на этой неделе")

    expires_at = get_expiration_date(now_datetime)

    evaluated_week_start = week_start - timedelta(weeks=1)

    try:
        with transaction.atomic():
            submission = Submission.objects.create(
                employee=employee,
                questionnaire=questionnaire,
                version_quest=version,
                department=department,
                week_start=week_start,
                evaluated_week_start=evaluated_week_start,
                expires_at=expires_at
            )

            Answer.objects.bulk_create([
                Answer(
                    submission=submission,
                    question_code=question_code,
                    value=value
                )
                for question_code, value in answers.items()
            ])
    except IntegrityError:
        if Submission.objects.filter(
            employee=employee,
            questionnaire=questionnaire,
            week_start=week_start,
        ).exists():
            raise ValidationError(
                "Вы уже проходили эту анкету на этой неделе"
            ) from None
        raise

    return submission

def _validate_answers(*, definition, answers):
    """Проверяет корректность ответа"""
    allowed_values = {}

    for category in definition["categories"]:
        for question in category["questions"]:
            allowed_values[question["code"]] = {
                option["value"]
                for option in question["answers"]
            }

    missing_codes = set(allowed_values) - set(answers)
    unknown_codes = set(answers) - set(allowed_values)

    if missing_codes:
        raise ValidationError("Нужно ответить на все вопросы")
    if unknown_codes:
        raise ValidationError("Переданы не известные вопросы")

    for question_code, value in answers.items():
        if type(value) is not int or value not in allowed_values[question_code]:
            raise ValidationError("Недопустимая оценка")
