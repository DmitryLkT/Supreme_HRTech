from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from users.models import Department
from ..models import Module, ModuleCompletion

class ModuleModelTest(TestCase):
    def test_module_created(self):
        """Создание модуля"""
        module = Module.objects.create(
            title="test",
            description="test",
        )

        self.assertIsNotNone(module.pk)

    def test_default_values(self):
        """Значения по умолчанию"""
        module = Module(
            title="test",
            description="test",
        )

        self.assertEqual(module.order, 0)
        self.assertEqual(module.is_published, False)
        self.assertEqual(module.content, "")

    def test_title_is_required(self):
        """Обязательное поле title"""
        module = Module(
            description="test",
        )

        with self.assertRaises(ValidationError) as context:
            module.full_clean()

        self.assertIn("title", context.exception.message_dict)


    def test_description_is_required(self):
        """Обязательное поле description"""
        module = Module(
            title="test",
        )


        with self.assertRaises(ValidationError) as context:
            module.full_clean()

        self.assertIn("description", context.exception.message_dict)

    def test_content_can_be_blank(self):
        """Валидация пустого content"""
        module = Module(
            title="test",
            description="test",
            content=""
        )

        module.full_clean()

    def test_title_max_length(self):
        """Ограничение длины title"""
        test = "t" * 201
        module = Module(
            title=test,
            description="test",
        )

        with self.assertRaises(ValidationError):
            module.full_clean()

    def test_order_cannot_be_negative(self):
        """Отрицательный order"""
        module = Module(
            title="test",
            description="test",
            order=-1,
        )
        with self.assertRaises(ValidationError) as context:
            module.full_clean()

        self.assertIn("order", context.exception.message_dict)

    def test_str_returns_title(self):
        """Строковое представление"""
        module = Module(
            title="test",
            description="test",
        )
        self.assertEqual(str(module), "test")

    def test_default_ordering(self):
        """Сортировка по умолчанию"""
        module1 = Module.objects.create(
            title="test",
            description="test",
            order=3
        )
        module2 = Module.objects.create(
            title="test",
            description="test",
            order=1
        )
        module3 = Module.objects.create(
            title="test",
            description="test",
            order=4
        )
        module4 = Module.objects.create(
            title="test",
            description="test",
            order=2
        )

        modules = [module2, module4, module1, module3]
        qs = list(Module.objects.all())

        self.assertEqual(qs, modules)

    def test_default_ordering_same_order_by_id(self):
        """Сортировка при одинаковом order"""

        module1 = Module.objects.create(
            title="test",
            description="test",
            order=1
        )
        module2 = Module.objects.create(
            title="test",
            description="test",
            order=1
        )
        module3 = Module.objects.create(
            title="test",
            description="test",
            order=1
        )

        modules = [module1, module2, module3]
        qs = list(Module.objects.all())

        self.assertEqual(qs, modules)

User = get_user_model()

class ModuleCompletionModelTest(TestCase):

    def setUp(self):
        """Создание пользователя и модуля для тестов."""

        self.department = Department.objects.create(
            name="test"
        )

        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
            department=self.department,
        )
        self.module = Module.objects.create(
            title="test",
            description="test",
        )

    def test_completion_created(self):
        """Создание записи о завершении модуля."""
        completion = ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertIsNotNone(completion.pk)

    def test_completed_at_is_set_automatically(self):
        """Автоматическое заполнение даты завершения."""
        completion = ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertIsNotNone(completion.completed_at)
        self.assertLessEqual(
            completion.completed_at,
            timezone.now(),
        )

    def test_user_is_required(self):
        """Обязательное поле user."""
        completion = ModuleCompletion(
            module=self.module,
        )

        with self.assertRaises(ValidationError) as context:
            completion.full_clean()

        self.assertIn("user", context.exception.message_dict)

    def test_module_is_required(self):
        """Обязательное поле module."""
        completion = ModuleCompletion(
            user=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            completion.full_clean()

        self.assertIn("module", context.exception.message_dict)

    def test_user_module_combination_must_be_unique(self):
        """Запрет повторного завершения одного модуля сотрудником."""
        ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ModuleCompletion.objects.create(
                    user=self.user,
                    module=self.module,
                )

    def test_same_module_can_be_completed_by_different_users(self):
        """Разные сотрудники могут завершить один модуль."""
        self.department = Department.objects.create(
            name="test2"
        )

        another_user = User.objects.create_user(
            username="anotheruser",
            password="testpassword123",
            department=self.department,
        )

        ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )
        completion = ModuleCompletion.objects.create(
            user=another_user,
            module=self.module,
        )

        self.assertIsNotNone(completion.pk)

    def test_same_user_can_complete_different_modules(self):
        """Один сотрудник может завершить разные модули."""
        another_module = Module.objects.create(
            title="another",
            description="another",
        )

        ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )
        completion = ModuleCompletion.objects.create(
            user=self.user,
            module=another_module,
        )

        self.assertIsNotNone(completion.pk)

    def test_str_returns_user_and_module(self):
        """Строковое представление завершения модуля."""
        completion = ModuleCompletion.objects.create(
            user=self.user,
            module=self.module,
        )

        self.assertEqual(
            str(completion),
            f"{self.user} - {self.module}",
        )