from django.test import TestCase

from .models import Questionnaire, QuestionnaireVersion
from .services.catalog_sync import sync_questionnaires

class QuestionnaireSyncTest(TestCase):
    def test_first_sync_publishes_wellbeing(self):
        self.assertEqual(Questionnaire.objects.count(), 0)
        sync_questionnaires()

        wellbeing = Questionnaire.objects.get(code="wellbeing")
        self.assertTrue(wellbeing.is_published)

        versions = QuestionnaireVersion.objects.filter(questionnaire=wellbeing).exists()
        self.assertTrue(versions)

    def test_sync_does_not_change_existing_publication_status(self):
        sync_questionnaires()
        wellbeing = Questionnaire.objects.get(code="wellbeing")

        wellbeing.is_published = False
        wellbeing.save(update_fields=["is_published"])
        sync_questionnaires()
        wellbeing.refresh_from_db()

        self.assertFalse(wellbeing.is_published)

    def test_sync_does_not_auto_publish_in_nonempty_catalog(self):
        Questionnaire.objects.create(code="existing", title="Анкета", description="Тестовая")
        sync_questionnaires()

        wellbeing = Questionnaire.objects.get(code="wellbeing")
        self.assertFalse(wellbeing.is_published)

    def test_sync_is_idempotent(self):
        sync_questionnaires()

        questionnaires_count = Questionnaire.objects.count()
        version_count = QuestionnaireVersion.objects.count()

        sync_questionnaires()

        self.assertEqual(Questionnaire.objects.count(), questionnaires_count)
        self.assertEqual(QuestionnaireVersion.objects.count(), version_count)



