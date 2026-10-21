from django.core.exceptions import ValidationError
from django.db import transaction

from health.models import Questionnaire

@transaction.atomic
def set_publication(*, questionnaire_ids, is_published):
    questionnaires = list(Questionnaire.objects.select_for_update().order_by("pk"))
    selected_ids = set(questionnaire_ids)

    has_published = any(
        is_published if item.pk in selected_ids else item.is_published
        for item in questionnaires
    )

    if not has_published:
        raise ValidationError(
            "Нельзя снять с публикации все анкеты. "
            "Хотя бы одна должна оставаться опубликованной.")

    return (
        Questionnaire.objects
        .filter(
            pk__in=selected_ids,
            is_published=not is_published,
        )
        .update(is_published=is_published)
    )
