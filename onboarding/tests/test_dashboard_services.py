from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from onboarding.models import Module, ModuleCompletion
from onboarding.services.employee_services import get_employees_queryset
from onboarding.services.module_services import get_number_published_modules
from onboarding.services.dashboard_services import calculate_general_statistics
from onboarding.services.dashboard_services import calculate_progress_percentage
from users.models import Department

User = get_user_model()

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
