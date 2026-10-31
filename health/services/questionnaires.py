from django.shortcuts import get_object_or_404

from health.models import QuestionnaireVersion,Submission

def get_questionnaire_version(version_id):
    """Возвращает опубликованную версию анкеты по id"""
    return get_object_or_404(
        QuestionnaireVersion.objects.select_related("questionnaire"),
        pk=version_id,
        questionnaire__is_published=True,
    )


def is_already_submitted(*, user, questionnaire, week_start):
    """Проверяет, проходил ли сотрудник анкету на этой неделе"""
    return Submission.objects.filter(
        employee=user, questionnaire=questionnaire, week_start=week_start,
    ).exists()


def build_questions(*, version):
    """Готовит вопросы версии анкеты для шаблона формы"""
    questions = []
    for category in version.definition["categories"]:
        for question in category["questions"]:
            questions.append({
                "id": question["code"],
                "text": question["text"],
                "is_required": True,
                "selected_id": None,
                "options": [
                    {"id": option["value"], "text": option["label"]}
                    for option in question["answers"]
                ],
            })
    return questions


def extract_answers(*, request, questions):
    """Извлекает ответы из POST и помечает выбранные варианты; возвращает (ответы, ошибка)"""
    answers = {}
    for question in questions:
        raw_value = request.POST.get("q_" + question["id"])
        if raw_value is None:
            continue
        try:
            value = int(raw_value)
        except ValueError:
            return None, "Некорректный ответ. Выберите вариант из списка."
        answers[question["id"]] = value
        question["selected_id"] = value
    return answers, None

def get_actual_questionnaire_version_id():
    """Возвращает id последней созданной версии опубликованной анкеты или None"""
    return (
        QuestionnaireVersion.objects
        .filter(questionnaire__is_published=True)
        .order_by("-created_at")          # проверь намерение: было "-questionnaire_id"
        .values_list("pk", flat=True)     # не тянем JSON-определение
        .first()
    )