from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Module, ModuleCompletion
from users.models import Department


class OnboardingTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.department = Department.objects.create(
            name="Тестовый отдел",
        )

        self.employee = User.objects.create_user(
            username="employee",
            password="test-password-123",
            department=self.department,
        )

        self.other_employee = User.objects.create_user(
            username="other_employee",
            password="test-password-456",
            department=self.department,
        )

        self.module = Module.objects.create(
            title="Знакомство с компанией",
            description="Первый модуль адаптации.",
            content="Добро пожаловать в команду!",
            order=1,
            is_published=True,
        )

        self.hidden_module = Module.objects.create(
            title="Черновик",
            description="Этот модуль пока не опубликован.",
            order=2,
            is_published=False,
        )

    def test_home_requires_login(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 302)

        expected_url = (
            f"{reverse('login')}?next={reverse('home')}"
        )

        self.assertRedirects(
            response,
            expected_url,
            fetch_redirect_response=False,
        )

    def test_hidden_module_returns_404(self):
        self.client.force_login(self.employee)

        url = reverse(
            "module_detail",
            kwargs={"module_id": self.hidden_module.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_completion_is_personal_and_not_duplicated(self):
        self.client.force_login(self.employee)

        url = reverse(
            "complete_module",
            kwargs={"module_id": self.module.id},
        )

        response = self.client.post(url)
        self.client.post(url)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            ModuleCompletion.objects.filter(
                user=self.employee,
                module=self.module,
            ).count(),
            1,
        )

        self.assertFalse(
            ModuleCompletion.objects.filter(
                user=self.other_employee,
                module=self.module,
            ).exists()
        )

    def test_home_shows_current_user_progress(self):
        ModuleCompletion.objects.create(
            user=self.employee,
            module=self.module,
        )

        self.client.force_login(self.employee)
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_modules"], 1)
        self.assertEqual(response.context["completed_count"], 1)
        self.assertEqual(response.context["progress_percent"], 100)

        self.client.force_login(self.other_employee)
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["completed_count"], 0)
        self.assertEqual(response.context["progress_percent"], 0)

    def test_completion_requires_post(self):
        self.client.force_login(self.employee)

        url = reverse(
            "complete_module",
            kwargs={"module_id": self.module.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(ModuleCompletion.objects.count(), 0)
