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
