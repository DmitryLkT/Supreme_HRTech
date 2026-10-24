from django.utils import timezone
from django.db.models import Avg, Count

from health.models import Submission

MIN_REPORT_PARTICIPANTS = 5

def get_report_submissions(*, questionnaire, period_start, period_end, department=None):
    """Возвращает непросроченные прохождения за оцениваемый период"""
    submissions = Submission.objects.filter(
        questionnaire=questionnaire,
        evaluated_week_start__gte=period_start,
        evaluated_week_start__lte=period_end,
        expires_at__gt=timezone.localdate()
    )

    if department is not None:
        submissions = submissions.filter(department=department)

    return submissions

def get_report_participation(*, questionnaire, period_start, period_end, department=None):
    """Проверяет, достаточно ли участников для показа отчёта"""
    submissions = get_report_submissions(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )

    participant_count = (
        submissions
        .order_by()
        .values("employee_id")
        .distinct()
        .count()
    )

    return {
        "participant_count": participant_count,
        "is_available": participant_count >= MIN_REPORT_PARTICIPANTS,
    }

def get_question_report(*, questionnaire, period_start, period_end, department=None,):
    """Возвращает средние оценки по вопросам с учётом порога участников"""
    participation = get_report_participation(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )

    if not participation["is_available"]:
        return {
            **participation,
            "questions": [],
        }

    submissions = get_report_submissions(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )

    question_stats = (
        submissions
        .filter(answers__isnull=False)
        .values("answers__question_code")
        .annotate(
            average_value=Avg("answers__value"),
            participant_count=Count("employee_id", distinct=True),
        )
        .filter(
            participant_count__gte=MIN_REPORT_PARTICIPANTS,
        )
        .order_by("answers__question_code")
    )

    return {
        **participation,
        "questions": [
            {
                "question_code": row["answers__question_code"],
                "average_value": round(row["average_value"], 2),
                "participant_count": row["participant_count"],
            }
            for row in question_stats
        ],
    }

def get_weekly_question_report(*, questionnaire, period_start, period_end, department=None,):
    """Возвращает средние оценки по вопросам и оцениваемым неделям"""
    submissions = get_report_submissions(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )

    weekly_stats = (
        submissions
        .filter(answers__isnull=False)
        .values(
            "evaluated_week_start",
            "answers__question_code",
        )
        .annotate(
            average_value=Avg("answers__value"),
            participant_count=Count("employee_id", distinct=True),
        )
        .filter(
            participant_count__gte=MIN_REPORT_PARTICIPANTS,
        )
        .order_by(
            "evaluated_week_start",
            "answers__question_code",
        )
    )

    return {
        "points": [
            {
                "week_start": row["evaluated_week_start"],
                "question_code": row["answers__question_code"],
                "average_value": round(row["average_value"], 2),
                "participant_count": row["participant_count"],
            }
            for row in weekly_stats
        ],
    }