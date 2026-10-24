from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.utils import timezone

from health.services.submissions import create_submission
from health.services.periods import get_week_start
from .models import QuestionnaireVersion, Submission

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


