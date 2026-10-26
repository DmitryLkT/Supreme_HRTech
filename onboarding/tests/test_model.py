from django.core.exceptions import ValidationError
from django.test import TestCase

from ..models import Module

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