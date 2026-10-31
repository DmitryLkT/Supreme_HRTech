from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone

from health.services.submissions import create_submission
from health.services.periods import get_week_start
from health.services.reports import get_report_participation, get_question_report, get_weekly_question_report, build_weekly_series
from health.services.questionnaires import get_questionnaire_version, is_already_submitted, build_questions, extract_answers, get_actual_questionnaire_version_id

from .models import QuestionnaireVersion, Submission
from .decorators import hr_required
from .froms import HRReportFilterForm

@login_required
def questionnaire_detail(request, version_id):
    """Открывает конкретную версию анкеты"""
    version = get_questionnaire_version(version_id)
    questionnaire = version.questionnaire
    week_start = get_week_start(timezone.localdate())

    if is_already_submitted(user=request.user, questionnaire=questionnaire, week_start=week_start):
        return render(request, "health/questionnaire_detail.html", {
            "version": version, "questionnaire": questionnaire,
            "state": "done", "week_start": week_start,
        })

    questions = build_questions(version=version)

    form_error = None
    if request.method == "POST":
        answers, form_error = extract_answers(request=request, questions=questions)
        if form_error is None:
            try:
                create_submission(
                    employee=request.user,
                    department=request.user.department,
                    version=version,
                    answers=answers,
                )
            except ValidationError as error:
                form_error = " ".join(error.messages)
            else:
                return redirect(request.path)

    return render(request, "health/questionnaire_detail.html", {
        "version": version,
        "questionnaire": questionnaire,
        "questions": questions,
        "state": "form",
        "form_error": form_error,
    })

@login_required
def health_entry(request):
    """Открывает актуальную версию опубликованной анкеты."""
    version_id = get_actual_questionnaire_version_id

    if version_id is None:
        raise Http404("Опубликованных анкет нет")

    return questionnaire_detail(request, version_id=version_id)

@hr_required
def hr_report(request):
    """Формирует HR-отчёт по анкетам за период с фильтрами"""
    form = HRReportFilterForm()
    state = "initial"
    participation = None
    question_report = None
    weekly_report = None
    weeks = []
    series = {}

    if request.GET.get("period_start") is not None:
        form = HRReportFilterForm(request.GET)
        if form.is_valid():
            state = "valid"

            questionnaire = form.cleaned_data["questionnaire"]
            period_start = form.cleaned_data["period_start"]
            period_end = form.cleaned_data["period_end"]
            department = form.cleaned_data["department"] or None   # "" → None

            participation = get_report_participation(
                questionnaire=questionnaire,
                period_start=period_start,
                period_end=period_end,
                department=department,
            )

            if participation["participant_count"] == 0:
                state = "empty"
            elif not participation["is_available"]:
                state = "insufficient"
            else:
                question_report = get_question_report(
                    questionnaire=questionnaire,
                    period_start=period_start,
                    period_end=period_end,
                    department=department,
                    participation=participation,        # не считаем дважды
                )
                weekly_report = get_weekly_question_report(
                    questionnaire=questionnaire,
                    period_start=period_start,
                    period_end=period_end,
                    department=department,
                )
                weeks, series = build_weekly_series(
                    weekly_report=weekly_report,
                    period_start=period_start,
                    period_end=period_end,
                )
        else:
            state = "invalid"

    return render(request, "health/hr_report.html", {
        "form": form, "state": state,
        "participation": participation,
        "question_report": question_report,
        "weekly_report": weekly_report,
        "weeks": weeks, "series": series,
    })

