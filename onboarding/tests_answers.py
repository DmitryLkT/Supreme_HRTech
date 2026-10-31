from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from users.models import Department

from .models import AnswerOption, AnswerSubmission, Module, Question


class AnswerSavingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        department = Department.objects.create(name="Тестовый отдел")
        call_command("setup_roles", stdout=StringIO())
        self.emp = User.objects.create_user("emp", password="pw-123456", department=department)
        self.emp2 = User.objects.create_user("emp2", password="pw-123456", department=department)
        self.hr = User.objects.create_user("hr", password="pw-123456", department=department)
        self.hr.groups.add(Group.objects.get(name="HR"))
        self.module = Module.objects.create(title="М1", description="d", order=1, is_published=True)
        self.scored = Question.objects.create(module=self.module, text="Сколько будет 2+2?", order=1)
        self.right = AnswerOption.objects.create(question=self.scored, text="4", is_correct=True)
        self.wrong = AnswerOption.objects.create(question=self.scored, text="5", is_correct=False)
        self.values = Question.objects.create(module=self.module, text="Что делать, если ошибся?", order=2)
        self.v1 = AnswerOption.objects.create(question=self.values, text="Сказать сразу", is_correct=True)
        self.v2 = AnswerOption.objects.create(question=self.values, text="Исправить молча", is_correct=True)
        self.ajax = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}

    def answer(self, question, option, **extra):
        return self.client.post(reverse("answer_question", args=[question.id]), {"option_id": option.id}, **extra)

    def test_scored_question_saved_and_graded(self):
        self.client.force_login(self.emp)
        data = self.answer(self.scored, self.wrong, **self.ajax).json()
        self.assertIs(data["is_correct"], False)
        self.assertTrue(data["scored"])
        self.assertIn("Правильный ответ: 4", data["message"])
        submission = AnswerSubmission.objects.get(user=self.emp, question=self.scored)
        self.assertEqual(submission.option, self.wrong)
        self.assertFalse(submission.is_correct)

    def test_retry_updates_single_row_and_counts_attempts(self):
        self.client.force_login(self.emp)
        self.answer(self.scored, self.wrong, **self.ajax)
        data = self.answer(self.scored, self.right, **self.ajax).json()
        self.assertTrue(data["is_correct"])
        self.assertEqual(AnswerSubmission.objects.count(), 1)
        submission = AnswerSubmission.objects.get()
        self.assertEqual(submission.option, self.right)
        self.assertEqual(submission.attempts, 2)
        self.assertTrue(submission.is_correct)

    def test_values_question_is_neutral(self):
        self.assertFalse(self.values.is_scored)
        self.assertTrue(self.scored.is_scored)
        self.client.force_login(self.emp)
        data = self.answer(self.values, self.v2, **self.ajax).json()
        self.assertIsNone(data["is_correct"])
        self.assertFalse(data["scored"])
        self.assertNotIn("Правильно", data["message"])
        self.assertNotIn("Неверно", data["message"])
        self.assertIsNone(AnswerSubmission.objects.get().is_correct)
        page = self.answer(self.values, self.v1)
        self.assertContains(page, "нет правильного и неправильного")
        self.assertNotContains(page, "✓ Правильно")

    def test_invalid_option_not_saved(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.answer(self.scored, self.v1, **self.ajax).status_code, 404)
        self.assertEqual(self.client.post(reverse("answer_question", args=[self.scored.id]), {}, **self.ajax).status_code, 400)
        self.assertEqual(AnswerSubmission.objects.count(), 0)

    def test_hr_cannot_submit(self):
        self.client.force_login(self.hr)
        self.assertEqual(self.answer(self.scored, self.right, **self.ajax).status_code, 403)
        self.assertEqual(AnswerSubmission.objects.count(), 0)

    def test_hr_summary_is_aggregate_and_protected(self):
        self.client.force_login(self.emp)
        self.answer(self.scored, self.right, **self.ajax)
        self.answer(self.values, self.v1, **self.ajax)
        self.client.force_login(self.emp2)
        self.answer(self.scored, self.wrong, **self.ajax)
        self.client.force_login(self.hr)
        page = self.client.get(reverse("hr_answers"))
        self.assertContains(page, "верно ответили 50%")
        self.assertContains(page, "1 · 50%")
        self.assertContains(page, "правильного ответа нет")
        self.assertNotContains(page, "emp2")
        self.assertEqual(self.client.get(reverse("hr_answers") + f"?module={self.module.id}").status_code, 200)
        self.assertEqual(self.client.get(reverse("hr_answers") + "?module=abc").status_code, 200)
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("hr_answers")).status_code, 403)

    def test_hr_employee_detail_shows_counts(self):
        self.client.force_login(self.emp)
        self.answer(self.scored, self.right, **self.ajax)
        self.answer(self.values, self.v1, **self.ajax)
        self.client.force_login(self.hr)
        page = self.client.get(reverse("hr_employee_detail", args=[self.emp.id]))
        self.assertContains(page, "верно: 1 из 1")

    def test_error_pages(self):
        response = self.client.get("/нет-такой-страницы/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Такой страницы нет", status_code=404)
