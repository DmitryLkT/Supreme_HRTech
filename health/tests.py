from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .models import AnswerUser, Questionnaire, QuestionnaireCompletion
from .scoring import category_scores, interpret
from .views import current_week_start


class ScoringTests(SimpleTestCase):
    def test_interpretation_boundaries(self):
        self.assertEqual(interpret(1.0)[0], "low")
        self.assertEqual(interpret(1.9)[0], "low")
        self.assertEqual(interpret(2.0)[0], "moderate")
        self.assertEqual(interpret(2.9)[0], "moderate")
        self.assertEqual(interpret(3.0)[0], "notable")
        self.assertEqual(interpret(3.9)[0], "notable")
        self.assertEqual(interpret(4.0)[0], "strong")
        self.assertEqual(interpret(5.0)[0], "strong")

    def test_category_is_mean_of_its_questions(self):
        # пример из задания: вопросы «Настроения» с оценками 2 и 3
        result = category_scores([("mood", 2), ("mood", 3), ("workload", 5)])
        mood = result[0]
        self.assertEqual(mood["key"], "mood")
        self.assertEqual(mood["average"], 2.5)
        self.assertEqual(mood["display"], "2,5")
        self.assertEqual(mood["level"], "moderate")
        self.assertEqual(result[1]["level"], "strong")


class HealthFlowTests(TestCase):
    def setUp(self):
        call_command("seed_health_questionnaire", stdout=StringIO())
        User = get_user_model()
        self.employee = User.objects.create_user("employee", password="pw-123456")
        self.other = User.objects.create_user("other", password="pw-123456")
        call_command("setup_roles", stdout=StringIO())
        self.hr = User.objects.create_user("hr", password="pw-123456")
        self.hr.groups.add(Group.objects.get(name="HR"))
        self.questionnaire = Questionnaire.objects.get(status="active")

    def answers(self, score=3, skip=None):
        data = {}
        for question in self.questionnaire.questionquestionnaire_set.all():
            if question.id == skip:
                continue
            option = question.answeroption_set.get(score=score)
            data[f"q_{question.id}"] = option.id
        return data

    def test_seed_creates_valid_active_questionnaire(self):
        self.assertEqual(self.questionnaire.questionquestionnaire_set.count(), 9)
        for question in self.questionnaire.questionquestionnaire_set.all():
            self.assertEqual(sorted(question.answeroption_set.values_list("score", flat=True)), [1, 2, 3, 4, 5])
        call_command("seed_health_questionnaire", stdout=StringIO())  # повторный запуск безопасен
        self.assertEqual(Questionnaire.objects.count(), 1)

    def test_form_requires_login(self):
        response = self.client.get(reverse("health_form"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_employee_sees_form_and_submits(self):
        self.client.force_login(self.employee)
        self.assertContains(self.client.get(reverse("health_form")), "Как прошла твоя рабочая неделя?")
        data = self.answers(4)
        data["comment"] = "Много дедлайнов"
        response = self.client.post(reverse("health_form"), data)
        self.assertRedirects(response, reverse("health_form"), fetch_redirect_response=False)
        completion = QuestionnaireCompletion.objects.get(user=self.employee)
        self.assertEqual(completion.week_start, current_week_start())
        self.assertEqual(completion.comment, "Много дедлайнов")
        self.assertEqual(AnswerUser.objects.filter(questionnaire_completion=completion).count(), 9)
        self.assertContains(self.client.get(reverse("health_form")), "Спасибо")

    def test_second_submission_in_same_week_is_ignored(self):
        self.client.force_login(self.employee)
        self.client.post(reverse("health_form"), self.answers(2))
        self.client.post(reverse("health_form"), self.answers(5))
        self.assertEqual(QuestionnaireCompletion.objects.filter(user=self.employee).count(), 1)
        self.assertEqual(AnswerUser.objects.filter(answer_option__score=5).count(), 0)

    def test_missing_required_answer_saves_nothing(self):
        self.client.force_login(self.employee)
        first = self.questionnaire.questionquestionnaire_set.first()
        response = self.client.post(reverse("health_form"), self.answers(3, skip=first.id))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Ответь на вопрос 1", status_code=400)
        self.assertEqual(QuestionnaireCompletion.objects.count(), 0)

    def test_option_from_another_question_is_rejected(self):
        self.client.force_login(self.employee)
        data = self.answers(3)
        first, second = list(self.questionnaire.questionquestionnaire_set.all())[:2]
        data[f"q_{first.id}"] = second.answeroption_set.get(score=3).id
        response = self.client.post(reverse("health_form"), data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuestionnaireCompletion.objects.count(), 0)

    def test_hr_sees_results_sorted_by_highest_signal(self):
        self.client.force_login(self.employee)
        self.client.post(reverse("health_form"), self.answers(2))
        self.client.logout()
        self.client.force_login(self.other)
        self.client.post(reverse("health_form"), self.answers(5))
        self.client.logout()

        self.client.force_login(self.hr)
        response = self.client.get(reverse("hr_health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["respondents"], 2)
        rows = list(response.context["page_obj"])
        self.assertEqual([r["user"].username for r in rows], ["other", "employee"])
        self.assertEqual(rows[0]["scores"][0]["level"], "strong")
        self.assertEqual(rows[1]["scores"][0]["level"], "moderate")

    def test_employee_cannot_open_hr_page(self):
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get(reverse("hr_health")).status_code, 403)

    def test_hr_cannot_fill_questionnaire(self):
        self.client.force_login(self.hr)
        self.assertEqual(self.client.get(reverse("health_form")).status_code, 403)

    def test_no_active_questionnaire_message(self):
        Questionnaire.objects.update(status="archived")
        self.client.force_login(self.employee)
        self.assertContains(self.client.get(reverse("health_form")), "Анкета пока не опубликована")
