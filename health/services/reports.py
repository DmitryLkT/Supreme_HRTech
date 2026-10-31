from datetime import timedelta

from django.utils import timezone
from django.db.models import Avg, Count

from health.models import QuestionnaireVersion, Submission

from health.services.periods import get_week_start

MIN_REPORT_PARTICIPANTS = 5


def get_report_submissions(*, questionnaire, period_start, period_end, department=None):
    """Возвращает непросроченные прохождения за оцениваемый период"""
    submissions = Submission.objects.filter(
        questionnaire=questionnaire,
        evaluated_week_start__gte=period_start,
        evaluated_week_start__lte=period_end,
        expires_at__gt=timezone.localdate(),
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
        submissions.order_by()
        .values("employee_id")
        .distinct()
        .count()
    )
    return {
        "participant_count": participant_count,
        "is_available": participant_count >= MIN_REPORT_PARTICIPANTS,
    }


def get_question_report(*, questionnaire, period_start, period_end,
                        department=None, participation=None):
    """Возвращает средние оценки по вопросам с учётом порога участников"""
    if participation is None:
        participation = get_report_participation(
            questionnaire=questionnaire,
            period_start=period_start,
            period_end=period_end,
            department=department,
        )

    if not participation["is_available"]:
        return {**participation, "questions": []}

    submissions = get_report_submissions(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )
    question_stats = _calculate_average_by_questions(
        submissions=submissions, group_fields=[],
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


def get_weekly_question_report(*, questionnaire, period_start, period_end, department=None):
    """Возвращает средние оценки по вопросам и оцениваемым неделям"""
    submissions = get_report_submissions(
        questionnaire=questionnaire,
        period_start=period_start,
        period_end=period_end,
        department=department,
    )

    question_codes = get_definition_question_codes(submissions=submissions)

    weekly_stats = _calculate_average_by_questions(
        submissions=submissions,
        group_fields=["evaluated_week_start"],
    )
    return {
        "question_codes": question_codes,
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


def get_definition_question_codes(*, submissions):
    """Возвращает коды вопросов из определений версий анкет в выборке"""
    version_ids = submissions.values_list("version_quest_id", flat=True).distinct()
    definitions = QuestionnaireVersion.objects.filter(
        pk__in=version_ids,
    ).values_list("definition", flat=True)

    codes = set()
    for definition in definitions:
        for category in definition["categories"]:
            for question in category["questions"]:
                codes.add(question["code"])
    return sorted(codes)


def build_weekly_series(*, weekly_report, period_start, period_end):
    """Формирует список недель периода и ряды средних оценок по вопросам"""
    weeks = []
    current_week = get_week_start(period_start)
    last_week = get_week_start(period_end)
    while current_week <= last_week:
        weeks.append(current_week)
        current_week += timedelta(weeks=1)

    week_index = {week: index for index, week in enumerate(weeks)}
    series = {code: [None] * len(weeks) for code in weekly_report["question_codes"]}
    for point in weekly_report["points"]:
        index = week_index.get(point["week_start"])
        if index is not None and point["question_code"] in series:
            series[point["question_code"]][index] = point["average_value"]
    return weeks, series


def _calculate_average_by_questions(*, submissions, group_fields):
    """Считает средние оценки и число участников; группы ниже порога скрываются"""
    return list(
        submissions
        .filter(answers__isnull=False)
        .values("answers__question_code", *group_fields)
        .annotate(
            average_value=Avg("answers__value"),
            participant_count=Count("employee_id", distinct=True),
        )
        .filter(participant_count__gte=MIN_REPORT_PARTICIPANTS)
        .order_by(*group_fields, "answers__question_code")
    )