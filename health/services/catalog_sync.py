from django.db import transaction

from ..definitions import QUESTIONNAIRE_DEFINITIONS
from ..models import Questionnaire, QuestionnaireVersion

@transaction.atomic
def sync_questionnaires():
    questionnaires_created = 0
    versions_created = 0
    questionnaires_updated = 0

    for definition in QUESTIONNAIRE_DEFINITIONS:
        code = definition["code"]
        title = definition["title"]
        description = definition["description"]
        version = definition["version"]

        questionnaire_obj, questionnaire_created = Questionnaire.objects.get_or_create(
            code=code, defaults={
                "title": title,
                "description": description
            })
        changed = False

        if questionnaire_created:
            questionnaires_created += 1
        else:
            changed = False

        if questionnaire_obj.title != title:
            questionnaire_obj.title = title
            changed = True

        if questionnaire_obj.description != description:
            questionnaire_obj.description = description
            changed = True

        if changed:
            questionnaire_obj.save(update_fields=["title", "description"])
            questionnaires_updated += 1

        version_object, version_created = QuestionnaireVersion.objects.get_or_create(
            questionnaire=questionnaire_obj,
            version=version,
            defaults={"definition" : definition}
        )

        if version_created: versions_created += 1

        if not version_created and version_object.definition != definition:
           raise ValueError( "Содержание существующей версии изменилось. Создай новую версию.")

    return {
        "questionnaires_created": questionnaires_created,
        "questionnaires_updated": questionnaires_updated,
        "versions_created": versions_created,
    }