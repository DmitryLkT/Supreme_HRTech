from django.db import transaction

from ..definitions import QUESTIONNAIRE_DEFINITIONS
from ..models import Questionnaire, QuestionnaireVersion
from .publication import set_publication

STARTER_QUESTIONNAIRE_CODE = "wellbeing"

@transaction.atomic
def sync_questionnaires():
    """Синхронизирует анкеты и версии с определениями из кода"""
    questionnaires_created = 0
    questionnaires_updated = 0
    versions_created = 0

    catalog_was_empty = not Questionnaire.objects.exists()

    for definition in QUESTIONNAIRE_DEFINITIONS:
        questionnaire_obj, questionnaire_created = Questionnaire.objects.get_or_create(
            code=definition["code"],
            defaults={
                "title": definition["title"],
                "description": definition["description"],
            },
        )
        if questionnaire_created:
            questionnaires_created += 1
        elif _apply_definition_changes(
                questionnaire=questionnaire_obj, definition=definition):
            questionnaires_updated += 1

        version_object, version_created = QuestionnaireVersion.objects.get_or_create(
            questionnaire=questionnaire_obj,
            version=definition["version"],
            defaults={"definition": definition},
        )
        if version_created:
            versions_created += 1
        elif version_object.definition != definition:
            raise ValueError(
                "Содержание существующей версии изменилось. Создай новую версию.")

    if catalog_was_empty:
        _publish_starter()

    return {
        "questionnaires_created": questionnaires_created,
        "questionnaires_updated": questionnaires_updated,
        "versions_created": versions_created,
    }


def _apply_definition_changes(*, questionnaire, definition):
    """Обновляет title и description анкеты из определения; True, если были изменения"""
    changed = False
    if questionnaire.title != definition["title"]:
        questionnaire.title = definition["title"]
        changed = True
    if questionnaire.description != definition["description"]:
        questionnaire.description = definition["description"]
        changed = True
    if changed:
        questionnaire.save(update_fields=["title", "description"])
    return changed


def _publish_starter():
    """Публикует стартовую анкету при первой синхронизации пустого каталога"""
    starter = Questionnaire.objects.get(code=STARTER_QUESTIONNAIRE_CODE)
    set_publication(questionnaire_ids=[starter.pk], is_published=True)