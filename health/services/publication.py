from django.core.exceptions import ValidationError
from django.db import transaction

from health.models import Questionnaire, QuestionnaireVersion

@transaction.atomic
def set_publication(*, questionnaire_ids, is_published):
    """Публикует или снимает анкеты с публикации с проверками целостности"""
    questionnaires = list(Questionnaire.objects.select_for_update().order_by("pk"))
    selected_ids = set(questionnaire_ids)

    if is_published:
        _ensure_have_versions(selected_ids=selected_ids)

    _ensure_published_remains(
        questionnaires=questionnaires,
        selected_ids=selected_ids,
        is_published=is_published,
    )

    return Questionnaire.objects.filter(
        pk__in=selected_ids,
        is_published=not is_published,
    ).update(is_published=is_published)


def _ensure_have_versions(*, selected_ids):
    """Запрещает публикацию анкет без единой версии"""
    without_versions = list(
        Questionnaire.objects
        .filter(pk__in=selected_ids)
        .exclude(pk__in=QuestionnaireVersion.objects
                 .values_list("questionnaire_id", flat=True))
        .values_list("code", flat=True)
    )
    if without_versions:
        raise ValidationError(
            "Нельзя опубликовать анкеты без версии: " + ", ".join(without_versions))


def _ensure_published_remains(*, questionnaires, selected_ids, is_published):
    """Запрещает снимать с публикации все анкеты сразу"""
    has_published = any(
        is_published if item.pk in selected_ids else item.is_published
        for item in questionnaires
    )
    if not has_published:
        raise ValidationError(
            "Нельзя снять с публикации все анкеты. "
            "Хотя бы одна должна оставаться опубликованной.")
