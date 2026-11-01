from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from onboarding.models import Module, ModuleCompletion
from onboarding.services.employee_services import get_employees_queryset
from onboarding.services.module_services import get_number_published_modules
from onboarding.services.dashboard_services import calculate_progress_percentage, calculate_progress_percent, calculate_general_statistics, calculate_answers_statistics
from users.models import Department

User = get_user_model()

class FakeInstance:
    """Хешируется по id, как Django-модель, — чтобы тесты вели себя как с реальными моделями"""

    def __init__(self, id, **fields):
        self.id = id
        self.__dict__.update(fields)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, FakeInstance):
            return self.id == other.id
        return NotImplemented


class FakeRelatedManager:
    """Имитирует менеджер обратной связи (.questions / .options) с методом .all()"""

    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return self._items


def make_option(option_id, text, is_correct=False):
    return FakeInstance(id=option_id, text=text, is_correct=is_correct)


def make_question(question_id, text, options, is_scored=True):
    return FakeInstance(id=question_id, text=text, is_scored=is_scored,
                        options=FakeRelatedManager(options))


def make_module(module_id, title, questions, is_published):
    return FakeInstance(id=module_id, title=title,
                        questions=FakeRelatedManager(questions), is_published=is_published)

class CalculateGeneralStatisticsTest(TestCase):
    def test_empty_list_employees(self):
        """Проверяет, что если список сотрудников пуст"""

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        self.assertEqual(employee_context['employees_count'], 0)
        self.assertEqual(employee_context['finished_count'], 0)
        self.assertEqual(employee_context['in_progress_count'], 0)
        self.assertEqual(employee_context['not_started_count'], 0)

    def test_no_one_started_employees(self):
        """Проверяет данные, когда никто из сотрудников еще не начал модули"""
        Module.objects.create(
            title="test",
            description="test",
            is_published=True,
        )

        department = Department.objects.create(
            name="test"
        )

        User.objects.create_user(
            username="testUser1",
            password="testPassword123",
            department=department,
        )
        User.objects.create_user(
            username="testUser2",
            password="testPassword321",
            department=department,
        )

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        self.assertEqual(employee_context['employees_count'], 2)
        self.assertEqual(employee_context['finished_count'], 0)
        self.assertEqual(employee_context['in_progress_count'], 0)
        self.assertEqual(employee_context['not_started_count'], 2)

    def test_everyone_has_finished(self):
        """Все сотрудники прошли все опубликованные модули"""
        module1 = Module.objects.create(
            title="test",
            description="test",
            is_published=True,
        )
        module2 = Module.objects.create(
            title="test2",
            description="test2",
            is_published=True,
        )

        department = Department.objects.create(
            name="test"
        )

        user1 = User.objects.create_user(
            username="testUser1",
            password="testPassword123",
            department=department,
        )
        user2 = User.objects.create_user(
            username="testUser2",
            password="testPassword321",
            department=department,
        )

        ModuleCompletion.objects.create(user=user1, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user1, module=module2, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user2, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user2, module=module2, completed_at=timezone.now())

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        self.assertEqual(employee_context['employees_count'], 2)
        self.assertEqual(employee_context['finished_count'], 2)
        self.assertEqual(employee_context['in_progress_count'], 0)
        self.assertEqual(employee_context['not_started_count'], 0)

    def test_mixed_case(self):
        """В одной выборке сотрудники во всех трёх состояниях"""
        module1 = Module.objects.create(
            title="test",
            description="test",
            is_published=True,
        )
        module2 = Module.objects.create(
            title="test2",
            description="test2",
            is_published=True,
        )

        department = Department.objects.create(
            name="test"
        )

        user1 = User.objects.create_user(
            username="testUser1",
            password="testPassword123",
            department=department,
        )
        user2 = User.objects.create_user(
            username="testUser2",
            password="testPassword321",
            department=department,
        )
        User.objects.create_user(
            username="testUser3",
            password="testPassword3211",
            department=department,
        )

        ModuleCompletion.objects.create(
            user=user1,
            module=module1,
            completed_at=timezone.now()
        )
        ModuleCompletion.objects.create(
            user=user1,
            module=module2,
            completed_at=timezone.now()
        )

        ModuleCompletion.objects.create(
            user=user2,
            module=module1,
            completed_at=timezone.now()
        )

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        self.assertEqual(employee_context['employees_count'], 3)
        self.assertEqual(employee_context['finished_count'], 1)
        self.assertEqual(employee_context['in_progress_count'], 1)
        self.assertEqual(employee_context['not_started_count'], 1)

    def test_borders(self):
        """Сотрудники с 0, total-1 и total пройденными модулями попадают в свои категории"""
        module1 = Module.objects.create(
            title="test",
            description="test",
            is_published=True,
        )
        module2 = Module.objects.create(
            title="test2",
            description="test2",
            is_published=True,
        )
        module3 = Module.objects.create(
            title="test3",
            description="test3",
            is_published=True,
        )

        department = Department.objects.create(
            name="test"
        )

        User.objects.create_user(
            username="testUser1",
            password="testPassword123",
            department=department,
        )
        user2 = User.objects.create_user(
            username="testUser2",
            password="testPassword321",
            department=department,
        )
        user3 = User.objects.create_user(
            username="testUser3",
            password="testPassword1243",
            department=department,
        )
        user4 = User.objects.create_user(
            username="testUser4",
            password="testPassword3211",
            department=department,
        )

        ModuleCompletion.objects.create(user=user2, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user3, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user3, module=module2, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user4, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user4, module=module2, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user4, module=module3, completed_at=timezone.now())

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        self.assertEqual(employee_context['employees_count'], 4)
        self.assertEqual(employee_context['finished_count'], 1)
        self.assertEqual(employee_context['in_progress_count'], 2)
        self.assertEqual(employee_context['not_started_count'], 1)

    def test_sum_invariant(self):
        """finished + in_progress + not_started равно employees_count"""
        module1 = Module.objects.create(
            title="test",
            description="test",
            is_published=True,
        )
        module2 = Module.objects.create(
            title="test2",
            description="test2",
            is_published=True,
        )

        department = Department.objects.create(
            name="test"
        )

        user1 = User.objects.create_user(
            username="testUser1",
            password="testPassword123",
            department=department,
        )
        user2 = User.objects.create_user(
            username="testUser2",
            password="testPassword321",
            department=department,
        )
        User.objects.create_user(
            username="testUser3",
            password="testPassword3211",
            department=department,
        )

        ModuleCompletion.objects.create(user=user1, module=module1, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user1, module=module2, completed_at=timezone.now())
        ModuleCompletion.objects.create(user=user2, module=module1, completed_at=timezone.now())

        employees = get_employees_queryset()
        total_modules = get_number_published_modules()

        self.assertEqual(total_modules, 2)

        employee_context = calculate_general_statistics(
            employees=employees,
            total_modules=total_modules
        )

        total_by_status = (
                employee_context['finished_count']
                + employee_context['in_progress_count']
                + employee_context['not_started_count']
        )
        self.assertEqual(total_by_status, employee_context['employees_count'])

class CalculateProgressPercentageTest(TestCase):
    def test_no_published_modules(self):
        """Если опубликованных модулей нет, progress_percent равен 0 у всех сотрудников на странице"""
        page = SimpleNamespace(object_list=[
            SimpleNamespace(completed_count=0),
            SimpleNamespace(completed_count=2),
        ])

        calculate_progress_percentage(page=page, total_modules=0)

        self.assertEqual(
            [employee.progress_percent for employee in page.object_list],
            [0, 0],
        )

    def test_nothing_has_been_covered(self):
        """Сотрудник с completed_count = 0 при total_modules = 3 должен получить progress_percent = 0"""
        page = SimpleNamespace(object_list=[
            SimpleNamespace(completed_count=0),
        ])

        calculate_progress_percentage(page=page, total_modules=3)

        self.assertEqual(
            [emp.progress_percent for emp in page.object_list],
            [0]
        )

    def test_everything_has_been_completed(self):
        """При completed_count == total_modules, ожидается 100"""
        page = SimpleNamespace(object_list=[
            SimpleNamespace(completed_count=2),
            SimpleNamespace(completed_count=2),
        ])

        calculate_progress_percentage(page=page, total_modules=2)

        self.assertEqual(
            [emp.progress_percent for emp in page.object_list],
            [100, 100]
        )

    def test_partial_completion(self):
        """Проверяет, что процент считается правильно, а округление ожидаемое"""
        page = SimpleNamespace(object_list=[
            SimpleNamespace(completed_count=1),
            SimpleNamespace(completed_count=2),
        ])

        calculate_progress_percentage(page=page, total_modules=3)

        self.assertEqual(
            [emp.progress_percent for emp in page.object_list],
            [33, 67]
        )

    def test_blank_page(self):
        """Проверяет, что цикл безопасен на пустом списке"""
        page = SimpleNamespace(object_list=[])

        calculate_progress_percentage(page=page, total_modules=1)

        self.assertEqual(
            [emp.progress_percent for emp in page.object_list],
            []
        )

class CalculateProgressPercentTest(TestCase):
    def test_zero_total_modules(self):
        """Если общее количество модулей равно 0, функция возвращает 0, а не падает с ZeroDivisionError"""
        result = calculate_progress_percent(completed_count=0, total_modules=0)

        self.assertEqual(result, 0)

    def test_completed_but_zero_total_modules(self):
        """Даже при наличии завершённых модулей total_modules = 0 защищает от деления на ноль"""
        result = calculate_progress_percent(completed_count=5, total_modules=0)

        self.assertEqual(result, 0)

    def test_nothing_has_been_completed(self):
        """Сотрудник с completed_count = 0 при total_modules = 3 получает 0%"""
        result = calculate_progress_percent(completed_count=0, total_modules=3)

        self.assertEqual(result, 0)

    def test_everything_has_been_completed(self):
        """При completed_count == total_modules результат равен 100"""
        result = calculate_progress_percent(completed_count=2, total_modules=2)

        self.assertEqual(result, 100)

    def test_partial_completion_rounds_down(self):
        """1 из 3 модулей — это 33.33...%, округляется до 33"""
        result = calculate_progress_percent(completed_count=1, total_modules=3)

        self.assertEqual(result, 33)

    def test_partial_completion_rounds_up(self):
        """2 из 3 модулей — это 66.66...%, округляется до 67"""
        result = calculate_progress_percent(completed_count=2, total_modules=3)

        self.assertEqual(result, 67)

    def test_bankers_rounding_on_half(self):
        """round() в Python округляет .5 по банковским правилам: 12.5 -> 12, а 37.5 -> 38"""
        self.assertEqual(
            calculate_progress_percent(completed_count=1, total_modules=8),
            12,
        )
        self.assertEqual(
            calculate_progress_percent(completed_count=3, total_modules=8),
            38,
        )

    def test_overcompletion_returns_more_than_100(self):
        """Если completed_count > total_modules (рассинхрон данных), процент превышает 100, а не обрезается"""
        result = calculate_progress_percent(completed_count=3, total_modules=2)

        self.assertEqual(result, 150)

class CalculateAnswersStatisticsTest(TestCase):
    def test_no_modules(self):
        """Пустой список модулей даёт пустой список блоков"""
        blocks = calculate_answers_statistics(modules=[], counts={})

        self.assertEqual(blocks, [])

    def test_module_without_questions(self):
        """Модуль без вопросов возвращается блоком с пустым списком questions"""
        module = make_module(1, "Модуль 1", [])

        blocks = calculate_answers_statistics(modules=[module], counts={})

        self.assertEqual(len(blocks), 1)
        self.assertIs(blocks[0]["module"], module)
        self.assertEqual(blocks[0]["questions"], [])

    def test_counts_are_keyed_by_option_id(self):
        """Регрессия: counts читается по option.id, поэтому total = сумма ответов по вариантам вопроса"""
        module = make_module(1, "Модуль 1", [
            make_question(1, "Вопрос", [
                make_option(101, "Вариант A", is_correct=True),
                make_option(102, "Вариант B", is_correct=False),
            ]),
        ])

        blocks = calculate_answers_statistics(
            modules=[module],
            counts={101: 3, 102: 7},
        )

        question = blocks[0]["questions"][0]
        self.assertEqual(question["total"], 10)
        self.assertEqual([row["count"] for row in question["rows"]], [3, 7])
        self.assertEqual([row["percent"] for row in question["rows"]], [30, 70])

    def test_all_answers_correct(self):
        """Все выбрали верный вариант — correct_percent = 100"""
        module = make_module(1, "Модуль 1", [
            make_question(1, "Вопрос", [
                make_option(101, "Верный", is_correct=True),
                make_option(102, "Неверный", is_correct=False),
            ]),
        ])

        blocks = calculate_answers_statistics(
            modules=[module],
            counts={101: 4, 102: 0},
        )

        question = blocks[0]["questions"][0]
        self.assertTrue(question["scored"])
        self.assertEqual(question["total"], 4)
        self.assertEqual(question["correct_percent"], 100)

    def test_no_correct_answers(self):
        """Никто не выбрал верный вариант — correct_percent = 0, а не None"""
        module = make_module(1, "Модуль 1", [
            make_question(1, "Вопрос", [
                make_option(101, "Верный", is_correct=True),
                make_option(102, "Неверный", is_correct=False),
            ]),
        ])

        blocks = calculate_answers_statistics(
            modules=[module],
            counts={101: 0, 102: 5},
        )

        question = blocks[0]["questions"][0]
        self.assertEqual(question["total"], 5)
        self.assertEqual(question["correct_percent"], 0)

    def test_unscored_question(self):
        """У неоцениваемого вопроса is_correct = None во всех строках и correct_percent = None, но проценты считаются"""
        module = make_module(1, "Модуль 1", [
            make_question(1, "Открытый вопрос", [
                make_option(101, "A", is_correct=True),
                make_option(102, "B", is_correct=False),
            ], is_scored=False),
        ])

        blocks = calculate_answers_statistics(
            modules=[module],
            counts={101: 3, 102: 1},
        )

        question = blocks[0]["questions"][0]
        self.assertFalse(question["scored"])
        self.assertIsNone(question["correct_percent"])
        self.assertEqual([row["is_correct"] for row in question["rows"]], [None, None])
        self.assertEqual([row["percent"] for row in question["rows"]], [75, 25])

    def test_total_equals_sum_of_counts(self):
        """total всегда равен сумме count по строкам — инвариант, который ломается при неверном ключе"""
        module = make_module(1, "Модуль 1", [
            make_question(1, "Вопрос", [
                make_option(101, "A", is_correct=True),
                make_option(102, "B", is_correct=False),
                make_option(103, "C", is_correct=True),
            ]),
        ])

        blocks = calculate_answers_statistics(
            modules=[module],
            counts={101: 3, 102: 4, 103: 5},
        )

        question = blocks[0]["questions"][0]
        self.assertEqual(question["total"], sum(row["count"] for row in question["rows"]))
