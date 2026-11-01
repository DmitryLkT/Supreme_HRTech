from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from ..models import Module, ModuleCompletion, Question, AnswerOption
from onboarding.services.module_services import (
    get_completion_dates_modules_employee,
    get_module,
    get_module_detail,
    get_number_published_modules,
    get_published_modules,
    get_published_modules_with_questions,
    get_selected_module,
)

from users.models import Department

User = get_user_model()


class ModuleServicesBase(TestCase):
    """Общий fixture: сотрудник, два опубликованных модуля, один черновик"""

    def setUp(self):
        self.department = Department.objects.create(name="test")
        self.user = User.objects.create_user(
            username="testuser", password="testpassword123", department=self.department,
        )
        self.published1 = Module.objects.create(
            title="pub1", description="d", is_published=True, order=1,
        )
        self.published2 = Module.objects.create(
            title="pub2", description="d", is_published=True, order=2,
        )
        self.unpublished = Module.objects.create(
            title="unpub", description="d", is_published=False,
        )

class GetModuleDetailTest(ModuleServicesBase):
    def test_returns_published_module(self):
        """Опубликованный модуль возвращается, is_completed = False без прохождения"""
        result = get_module_detail(user=self.user, module_id=self.published1.id)

        self.assertEqual(result["module"], self.published1)
        self.assertFalse(result["is_completed"])

    def test_is_completed_true(self):
        """Сотрудник прошёл модуль — is_completed = True"""
        ModuleCompletion.objects.create(user=self.user, module=self.published1)

        result = get_module_detail(user=self.user, module_id=self.published1.id)

        self.assertTrue(result["is_completed"])

    def test_completion_of_other_user_does_not_count(self):
        """Чужое прохождение не делает модуль завершённым для этого сотрудника"""
        other = User.objects.create_user(
            username="other", password="testpassword123", department=self.department,
        )
        ModuleCompletion.objects.create(user=other, module=self.published1)

        result = get_module_detail(user=self.user, module_id=self.published1.id)

        self.assertFalse(result["is_completed"])

    def test_404_for_unpublished_module(self):
        """Неопубликованный модуль недоступен — Http404"""
        with self.assertRaises(Http404):
            get_module_detail(user=self.user, module_id=self.unpublished.id)

    def test_404_for_missing_module(self):
        """Несуществующий id — Http404"""
        with self.assertRaises(Http404):
            get_module_detail(user=self.user, module_id=999999)

    def test_prefetches_questions_and_options(self):
        """prefetch_related подгружает вопросы и варианты: доступ без доп. запросов"""
        question = Question.objects.create(module=self.published1, text="q?")
        AnswerOption.objects.create(question=question, text="opt")

        result = get_module_detail(user=self.user, module_id=self.published1.id)

        with self.assertNumQueries(0):
            options = [o for q in result["module"].questions.all() for o in q.options.all()]
        self.assertEqual(len(options), 1)

class GetModuleTest(ModuleServicesBase):
    def test_returns_published_module(self):
        """Возвращает найденный опубликованный модуль"""
        module = get_module(user=self.user, module_id=self.published1.id)

        self.assertEqual(module, self.published1)

    def test_creates_completion(self):
        """Создаёт запись о прохождении"""
        get_module(user=self.user, module_id=self.published1.id)

        self.assertTrue(
            ModuleCompletion.objects.filter(user=self.user, module=self.published1).exists()
        )

    def test_second_call_does_not_duplicate_completion(self):
        """Повторный вызов не создаёт вторую запись (unique-констрейнт не падает)"""
        get_module(user=self.user, module_id=self.published1.id)
        get_module(user=self.user, module_id=self.published1.id)

        self.assertEqual(
            ModuleCompletion.objects.filter(user=self.user, module=self.published1).count(),
            1,
        )

    def test_completion_not_created_for_other_modules(self):
        """Прохождение создаётся только для запрошенного модуля"""
        get_module(user=self.user, module_id=self.published1.id)

        self.assertFalse(
            ModuleCompletion.objects.filter(user=self.user, module=self.published2).exists()
        )

    def test_404_for_unpublished_module(self):
        """Неопубликованный модуль недоступен — Http404"""
        with self.assertRaises(Http404):
            get_module(user=self.user, module_id=self.unpublished.id)

    def test_404_for_missing_module(self):
        """Несуществующий id — Http404"""
        with self.assertRaises(Http404):
            get_module(user=self.user, module_id=999999)

class GetPublishedModulesTest(ModuleServicesBase):
    def test_returns_only_published(self):
        """Возвращаются только опубликованные модули"""
        self.assertEqual(get_published_modules(), [self.published1, self.published2])

    def test_returns_list(self):
        """Результат — именно list, а не QuerySet"""
        self.assertIsInstance(get_published_modules(), list)

    def test_empty_when_nothing_published(self):
        """Ничего не опубликовано — пустой список"""
        Module.objects.all().update(is_published=False)

        self.assertEqual(get_published_modules(), [])

    def test_respects_default_ordering(self):
        """Порядок соответствует Meta.ordering = (order, id)"""
        Module.objects.all().delete()
        first = Module.objects.create(title="a", description="d", is_published=True, order=2)
        second = Module.objects.create(title="b", description="d", is_published=True, order=1)

        self.assertEqual(get_published_modules(), [second, first])


class GetPublishedModulesWithQuestionsTest(ModuleServicesBase):
    def test_returns_only_published(self):
        """Возвращаются только опубликованные модули"""
        question = Question.objects.create(module=self.published1, text="q?")
        AnswerOption.objects.create(question=question, text="opt")

        modules = get_published_modules_with_questions()

        self.assertEqual(modules, [self.published1, self.published2])

    def test_prefetches_without_extra_queries(self):
        """Всё дерево модули→вопросы→варианты читается за 3 запроса"""
        question = Question.objects.create(module=self.published1, text="q?")
        AnswerOption.objects.create(question=question, text="opt1")
        AnswerOption.objects.create(question=question, text="opt2")

        with self.assertNumQueries(3):  # модули + вопросы + варианты
            modules = get_published_modules_with_questions()
            _ = [o for m in modules for q in m.questions.all() for o in q.options.all()]


class GetNumberPublishedModulesTest(ModuleServicesBase):
    def test_counts_only_published(self):
        """Считаются только опубликованные модули"""
        self.assertEqual(get_number_published_modules(), 2)

    def test_zero_when_nothing_published(self):
        """Ничего не опубликовано — 0"""
        Module.objects.all().update(is_published=False)

        self.assertEqual(get_number_published_modules(), 0)

class GetCompletionDatesModulesEmployeeTest(ModuleServicesBase):
    def test_empty_dict_for_employee_without_completions(self):
        """Нет прохождений — пустой словарь"""
        self.assertEqual(get_completion_dates_modules_employee(self.user), {})

    def test_maps_module_id_to_date(self):
        """Ключ — id модуля, значение — дата завершения"""
        completion = ModuleCompletion.objects.create(user=self.user, module=self.published1)

        dates = get_completion_dates_modules_employee(self.user)

        self.assertEqual(dates, {self.published1.id: completion.completed_at})

    def test_ignores_unpublished_modules(self):
        """Прохождения неопубликованных модулей не попадают в словарь"""
        ModuleCompletion.objects.create(user=self.user, module=self.unpublished)

        self.assertEqual(get_completion_dates_modules_employee(self.user), {})

    def test_ignores_other_employees(self):
        """Чужие прохождения не попадают в словарь"""
        other = User.objects.create_user(
            username="other", password="testpassword123", department=self.department,
        )
        ModuleCompletion.objects.create(user=other, module=self.published1)

        self.assertEqual(get_completion_dates_modules_employee(self.user), {})

    def test_multiple_modules(self):
        """Несколько прохождений — несколько записей с правильными датами"""
        c1 = ModuleCompletion.objects.create(user=self.user, module=self.published1)
        c2 = ModuleCompletion.objects.create(user=self.user, module=self.published2)

        dates = get_completion_dates_modules_employee(self.user)

        self.assertEqual(
            dates,
            {self.published1.id: c1.completed_at, self.published2.id: c2.completed_at},
        )

class GetSelectedModuleTest(ModuleServicesBase):
    def test_returns_module_by_valid_id(self):
        """Числовой GET-параметр с id из списка возвращает модуль"""
        result = get_selected_module(
            modules=[self.published1, self.published2], raw=str(self.published2.id),
        )

        self.assertEqual(result, self.published2)

    def test_returns_none_for_id_not_in_list(self):
        """Числовой id, которого нет в списке — None"""
        result = get_selected_module(modules=[self.published1], raw=str(self.published2.id))

        self.assertIsNone(result)

    def test_returns_none_for_non_numeric_raw(self):
        """Нечисловой параметр — None"""
        self.assertIsNone(get_selected_module(modules=[self.published1], raw="abc"))
        self.assertIsNone(get_selected_module(modules=[self.published1], raw=""))

    def test_returns_none_for_decimal_with_garbage(self):
        """Строки вида '1a', '-1', '1.5' не проходят isdecimal"""
        self.assertIsNone(get_selected_module(modules=[self.published1], raw="1a"))
        self.assertIsNone(get_selected_module(modules=[self.published1], raw="-1"))
        self.assertIsNone(get_selected_module(modules=[self.published1], raw="1.5"))

    def test_returns_none_for_empty_modules_list(self):
        """Пустой список модулей — None"""
        self.assertIsNone(get_selected_module(modules=[], raw=str(self.published1.id)))

    def test_first_match_wins_on_duplicate_ids(self):
        """При дубликатах в списке возвращается первый"""
        result = get_selected_module(
            modules=[self.published1, self.published2, self.published1],
            raw=str(self.published1.id),
        )

        self.assertIs(result, self.published1)