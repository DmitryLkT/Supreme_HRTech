from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from users.models import Department
from django.urls import reverse
from django.utils import timezone

from .models import MentorQuestion, PathProgress, PathStep
from .views import current_period, day_of_path


class Base(TestCase):
    def setUp(self):
        User = get_user_model()
        department = Department.objects.create(name="Тестовый отдел")
        call_command("setup_roles", stdout=StringIO())
        self.emp = User.objects.create_user("emp", password="pw-123456", department=department)
        self.emp2 = User.objects.create_user("emp2", password="pw-123456", department=department)
        self.hr = User.objects.create_user("hr", password="pw-123456", department=department)
        self.hr.groups.add(Group.objects.get(name="HR"))
        self.admin = User.objects.create_superuser("root", password="pw-123456", department=department.id)


class PathTests(Base):
    def setUp(self):
        super().setUp()
        self.s1 = PathStep.objects.create(period=30, title="Шаг 1", order=1)
        self.s2 = PathStep.objects.create(period=60, title="Шаг 2", order=1)
        PathStep.objects.create(period=90, title="Скрытый", is_published=False)

    def test_period_and_day_math(self):
        self.assertEqual([current_period(d) for d in (1, 30, 31, 60, 61, 90)], [30, 30, 60, 60, 90, 90])
        self.emp.date_joined = timezone.now() - timedelta(days=200)
        self.assertEqual(day_of_path(self.emp), 90)
        self.emp.date_joined = timezone.now()
        self.assertEqual(day_of_path(self.emp), 1)

    def test_requires_login_and_hides_unpublished(self):
        self.assertEqual(self.client.get(reverse("path")).status_code, 302)
        self.client.force_login(self.emp)
        response = self.client.get(reverse("path"))
        self.assertContains(response, "Шаг 1")
        self.assertNotContains(response, "Скрытый")

    def test_toggle_is_per_user_and_reversible(self):
        self.client.force_login(self.emp)
        url = reverse("toggle_step", args=[self.s1.id])
        self.client.post(url)
        self.assertTrue(PathProgress.objects.filter(user=self.emp, step=self.s1).exists())
        self.assertFalse(PathProgress.objects.filter(user=self.emp2).exists())
        self.client.post(url)
        self.assertFalse(PathProgress.objects.filter(user=self.emp, step=self.s1).exists())

    def test_toggle_needs_post_and_published_step(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("toggle_step", args=[self.s1.id])).status_code, 405)
        hidden = PathStep.objects.get(title="Скрытый")
        self.assertEqual(self.client.post(reverse("toggle_step", args=[hidden.id])).status_code, 404)

    def test_hr_sees_aggregate_and_cannot_use_employee_page(self):
        PathProgress.objects.create(user=self.emp, step=self.s1)
        self.client.force_login(self.hr)
        response = self.client.get(reverse("hr_path"))
        self.assertContains(response, "1 из 2")
        self.assertEqual(self.client.get(reverse("path")).status_code, 403)
        self.client.force_login(self.emp)
        self.assertEqual(self.client.get(reverse("hr_path")).status_code, 403)

    def test_empty_state_and_seed(self):
        PathStep.objects.all().delete()
        self.client.force_login(self.emp)
        self.assertContains(self.client.get(reverse("path")), "План пока не заполнен")
        call_command("seed_path_steps", stdout=StringIO())
        count = PathStep.objects.count()
        call_command("seed_path_steps", stdout=StringIO())
        self.assertEqual(PathStep.objects.count(), count)
        self.assertTrue(PathStep.objects.filter(is_placeholder=True).count() == count)
        self.assertContains(self.client.get(reverse("path")), "ЗАПОЛНЯЕТСЯ КОМПАНИЕЙ")


class MentorTests(Base):
    def test_employee_asks_and_sees_only_own(self):
        MentorQuestion.objects.create(user=self.emp2, text="Чужой вопрос")
        self.client.force_login(self.emp)
        response = self.client.post(reverse("mentor"), {"category": "process", "text": "  Как согласовать?  "})
        self.assertRedirects(response, reverse("mentor"))
        question = MentorQuestion.objects.get(user=self.emp)
        self.assertEqual(question.text, "Как согласовать?")
        self.assertEqual(question.category, "process")
        page = self.client.get(reverse("mentor"))
        self.assertContains(page, "Как согласовать?")
        self.assertNotContains(page, "Чужой вопрос")

    def test_validation(self):
        self.client.force_login(self.emp)
        self.assertEqual(self.client.post(reverse("mentor"), {"text": "   "}).status_code, 400)
        self.assertEqual(self.client.post(reverse("mentor"), {"text": "я" * 1001}).status_code, 400)
        self.assertEqual(MentorQuestion.objects.count(), 0)
        self.client.post(reverse("mentor"), {"category": "ерунда", "text": "ok"})
        self.assertEqual(MentorQuestion.objects.get().category, "other")

    def test_hr_answers_and_employee_sees_answer(self):
        question = MentorQuestion.objects.create(user=self.emp, text="Где шаблон?")
        self.client.force_login(self.hr)
        self.assertContains(self.client.get(reverse("hr_mentor")), "Где шаблон?")
        self.client.post(reverse("hr_mentor_answer", args=[question.id]), {"answer": "В общей папке."})
        question.refresh_from_db()
        self.assertEqual(question.answer, "В общей папке.")
        self.assertEqual(question.answered_by, self.hr)
        self.assertIsNotNone(question.answered_at)
        self.client.force_login(self.emp)
        self.assertContains(self.client.get(reverse("mentor")), "В общей папке.")

    def test_employee_cannot_answer_or_open_hr_page(self):
        question = MentorQuestion.objects.create(user=self.emp, text="Q")
        self.client.force_login(self.emp)
        self.assertEqual(self.client.post(reverse("hr_mentor_answer", args=[question.id]), {"answer": "x"}).status_code, 403)
        self.assertEqual(self.client.get(reverse("hr_mentor")).status_code, 403)

    def test_empty_answer_ignored_and_html_escaped(self):
        question = MentorQuestion.objects.create(user=self.emp, text="<script>alert(1)</script>")
        self.client.force_login(self.hr)
        self.client.post(reverse("hr_mentor_answer", args=[question.id]), {"answer": "   "})
        question.refresh_from_db()
        self.assertEqual(question.answer, "")
        self.assertNotContains(self.client.get(reverse("hr_mentor")), "<script>alert(1)</script>")
