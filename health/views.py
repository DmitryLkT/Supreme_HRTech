from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone

from health.services.submissions import create_submission
from health.services.periods import get_week_start
from health.services.reports import get_report_participation, get_question_report, get_weekly_question_report
from .models import QuestionnaireVersion, Submission
from .decorators import hr_required
from .froms import HRReportFilterForm

@login_required
def questionnaire_detail(request, version_id):
    """Открывает конкретную версию анкеты"""
    version = get_object_or_404(
        QuestionnaireVersion.objects.select_related("questionnaire"),
        pk=version_id,
        questionnaire__is_published=True
    )

    week_start = get_week_start(timezone.localdate())

    already_submitted = Submission.objects.filter(
        employee=request.user,
        questionnaire=version.questionnaire,
        week_start=week_start,
    ).exists()

    if already_submitted:
        return render(
            request,
            "health/questionnaire_detail.html",
            {
                "version": version,
                "questionnaire": version.questionnaire,
                "state": "done",
                "week_start": week_start,
            },
        )

    questions = []

    for category in version.definition["categories"]:
        for question in category["questions"]:
            questions.append({
                "id": question["code"],
                "text": question["text"],
                "is_required": True,
                "selected_id": None,
                "options": [
                    {
                        "id": option["value"],
                        "text": option["label"]
                    }
                    for option in question["answers"]
                ]
            })

    form_error = None

    if request.method == "POST":
        answers = {}

        try:
            for question in questions:
                field_name = "q_" + question["id"]
                raw_value = request.POST.get(field_name)

                if raw_value is None:
                    continue

                value = int(raw_value)
                answers[question["id"]] = value
                question["selected_id"] = value

            create_submission(
                employee=request.user,
                department=request.user.department,
                version=version,
                answers=answers,
            )

        except ValueError:
            form_error = "Некорректный ответ. Выберите вариант из списка."

        except ValidationError as error:
            form_error = " ".join(error.messages)

        else:
            return redirect(request.path)

    return render(
        request,
        "health/questionnaire_detail.html",
        {
            "version": version,
            "questionnaire": version.questionnaire,
            "questions": questions,
            "state": "form",
            "form_error": form_error,
        }
    )

@hr_required
def hr_report(request):
    form = HRReportFilterForm()
    state = "initial"
    participation = None
    question_report = None
    weekly_report = None

    if request.GET.get("period_start") is not None:
        form = HRReportFilterForm(request.GET)
        if form.is_valid():
            state = "valid"

            questionnaire = form.cleaned_data["questionnaire"]
            period_start = form.cleaned_data["period_start"]
            period_end = form.cleaned_data["period_end"]
            department =  form.cleaned_data["department"]
            if department == "":
                department = None

            participation = get_report_participation(
                questionnaire=questionnaire,
                period_start=period_start,
                period_end=period_end,
                department=department)

            if participation["participant_count"] == 0:
                state = "empty"
            elif participation["is_available"] is False:
                state = "insufficient"
            else:
                question_report = get_question_report(
                    questionnaire=questionnaire,
                    period_start=period_start,
                    period_end=period_end,
                    department=department)
                weekly_report = get_weekly_question_report(
                    questionnaire=questionnaire,
                    period_start=period_start,
                    period_end=period_end,
                    department=department)
        else:
            state = "invalid"

    return render(request,
                  "health/hr_report.html",
                  {
                      "form": form,
                      "state": state,
                      "participation": participation,
                      "question_report": question_report,
                      "weekly_report": weekly_report,
                  })

