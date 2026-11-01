import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import Http404
from django.test import TestCase
from django.utils import timezone

from onboarding.models import Module, ModuleCompletion
from onboarding.services.employee_services import (
    filtering_employees_words,
    add_completion_date_each_module,
    employees_queryset,
    get_employee,
    get_employees_queryset,
)

from users.models import Department

User = get_user_model()

def make_user(username, department, **extra):
    """Создаёт обычного сотрудника; department обязателен (NOT NULL в схеме)"""
    defaults = {"password": "testPassword123"}
    defaults.update(extra)
    return User.objects.create_user(username=username, department=department, **defaults)

class FilteringEmployeesWordsTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="testDepartment",
        )

        self.user1 = make_user(
            username="testUser1",
            first_name="testFirstName1",
            last_name="testLastName1",
            password="testPassword123",
            department=self.department
        )

        self.user2 = make_user(
            username="testUser2",
            first_name="testFirstName2",
            last_name="testLastName2",
            password="testPassword321",
            department=self.department
        )

        self.user3 = make_user(
            username="testUser3",
            first_name="testFirstName3",
            last_name="testLastName3",
            password="testPassword3211",
            department=self.department
        )

    def test_empty_request(self):
        """Ловит ошибку, когда пустой запрос скрывает всех"""
        query = ""
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(
            employees,
            [self.user1, self.user2, self.user3],
            ordered=False
        )

    def test_spaces_edges_between_words(self):
        """Проверяет работу разбиении строки."""
        query = " testFirstName3    testLastName3   "
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(employees,[self.user3])

    def test_search_login(self):
        """Слово совпадает только с username"""
        query = "testUser1"
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(employees,[self.user1])

    def test_search_first_name(self):
        """Слово совпадает только с first_name"""
        query = "testFirstName1"
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(employees,[self.user1])

    def test_search_last_name(self):
        """Слово совпадает только с last_name"""
        query = "testLastName1"
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(employees,[self.user1])

    def test_case_not_important(self):
        """Проверяет, что регистр не важен"""
        query = "TESTUSER1"
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(employees, [self.user1])

    def test_partial_match(self):
        """Проверка на частичное совподение"""
        query = "testU"
        employees = get_employees_queryset()

        employees = filtering_employees_words(query=query, employees=employees)

        self.assertQuerySetEqual(
            employees,
            [self.user1, self.user2, self.user3],
            ordered=False
        )

class EmployeesQuerysetTest(TestCase):
    """Тестируем employees_queryset() — базовый фильтр сотрудников"""

    def setUp(self):
        self.department = Department.objects.create(name="testDepartment")
        self.employee = make_user(
            "employee",
            first_name="Ivan",
            last_name="Ivanov",
            department=self.department,
        )

    def test_hides_inactive_user(self):
        """Неактивный пользователь не попадает в выборку"""
        inactive = make_user("inactive", self.department)
        inactive.is_active = False
        inactive.save()

        employees = employees_queryset()

        self.assertQuerySetEqual(employees, [self.employee], ordered=False)

    def test_hides_superuser(self):
        """Суперпользователь не попадает в выборку"""
        make_user("super", self.department, is_superuser=True)

        employees = employees_queryset()

        self.assertQuerySetEqual(employees, [self.employee], ordered=False)

    def test_hides_staff_user(self):
        """Пользователь с is_staff=True не попадает в выборку"""
        make_user("staffer", self.department, is_staff=True)

        employees = employees_queryset()

        self.assertQuerySetEqual(employees, [self.employee], ordered=False)

    def test_hides_hr_group_member(self):
        """Пользователь в группе HR не попадает в выборку"""
        hr_group = Group.objects.create(name="HR")
        hr = make_user("hr", self.department)
        hr.groups.add(hr_group)

        employees = employees_queryset()

        self.assertQuerySetEqual(employees, [self.employee], ordered=False)

    def test_returns_only_employees(self):
        """В выборку попадает только обычный активный сотрудник без прав"""
        make_user("inactive", self.department, is_active=False)
        make_user("super", self.department, is_superuser=True)
        make_user("staffer", self.department, is_staff=True)
        hr_group = Group.objects.create(name="HR")
        hr = make_user("hr", self.department)
        hr.groups.add(hr_group)

        employees = employees_queryset()

        self.assertQuerySetEqual(employees, [self.employee], ordered=False)


class GetEmployeesQuerysetTest(TestCase):
    """Тестируем get_employees_queryset() — annotate completed_count / last_completed_at"""

    def setUp(self):
        self.department = Department.objects.create(name="testDepartment")
        self.user = make_user(
            "employee",
            first_name="Ivan",
            last_name="Ivanov",
            department=self.department,
        )
        self.module1 = Module.objects.create(title="m1", is_published=True)
        self.module2 = Module.objects.create(title="m2", is_published=True)

    def test_annotates_zero_for_user_without_completions(self):
        """Сотрудник без прохождений получает completed_count = 0 и last_completed_at = None"""
        employee = get_employees_queryset().get(pk=self.user.pk)

        self.assertEqual(employee.completed_count, 0)
        self.assertIsNone(employee.last_completed_at)

    def test_completed_count_counts_only_published(self):
        """Непубликованный модуль не влияет на completed_count"""
        unpublished = Module.objects.create(title="m3", is_published=False)
        ModuleCompletion.objects.create(
            user=self.user, module=unpublished, completed_at=timezone.now()
        )

        employee = get_employees_queryset().get(pk=self.user.pk)

        self.assertEqual(employee.completed_count, 0)

    def test_last_completed_at_takes_max_over_published(self):
        """last_completed_at — максимум дат по опубликованным модулям, неопубликованные игнорируются.
        Даты проставляем через .update(), потому что auto_now перезаписывает create()"""
        late = timezone.make_aware(datetime.datetime(2026, 6, 1, 10, 0))

        ModuleCompletion.objects.create(user=self.user, module=self.module1)
        ModuleCompletion.objects.filter(user=self.user, module=self.module1).update(
            completed_at=late
        )

        # Неопубликованный модуль с той же датой — не должен влиять ни на count, ни на max
        unpublished = Module.objects.create(title="m3", is_published=False)
        ModuleCompletion.objects.create(user=self.user, module=unpublished)
        ModuleCompletion.objects.filter(user=self.user, module=unpublished).update(
            completed_at=late
        )

        employee = get_employees_queryset().get(pk=self.user.pk)

        self.assertEqual(employee.last_completed_at, late)
        self.assertEqual(employee.completed_count, 1)


class GetEmployeeTest(TestCase):
    """Тестируем get_employee() — get_object_or_404 поверх employees_queryset"""

    def setUp(self):
        self.department = Department.objects.create(name="testDepartment")
        self.user = make_user("employee", department=self.department)

    def test_returns_employee(self):
        """Существующий id возвращает сотрудника"""
        employee = get_employee(self.user.pk)

        self.assertEqual(employee.pk, self.user.pk)

    def test_404_for_missing_id(self):
        """Несуществующий id вызывает Http404"""
        with self.assertRaises(Http404):
            get_employee(999999)

    def test_404_for_hidden_user(self):
        """id суперпользователя (вне employees_queryset) вызывает Http404, а не возвращает его"""
        superuser = make_user("super", self.department,is_superuser=True)

        with self.assertRaises(Http404):
            get_employee(superuser.pk)


class AddCompletionDateEachModuleTest(TestCase):
    """Тестируем add_completion_date_each_module()"""

    def setUp(self):
        self.department = Department.objects.create(name="testDepartment")

        self.user = make_user("employee", self.department)
        self.module1 = Module.objects.create(title="m1", is_published=True)
        self.module2 = Module.objects.create(title="m2", is_published=True)

    def test_sets_dates_on_modules(self):
        """Каждому модулю проставляется его дата завершения"""
        date1 = timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0))
        date2 = timezone.make_aware(datetime.datetime(2026, 6, 1, 10, 0))
        completions = {self.module1.id: date1, self.module2.id: date2}
        modules = [self.module1, self.module2]

        add_completion_date_each_module(modules=modules, completions=completions)

        self.assertEqual(self.module1.employee_completed_at, date1)
        self.assertEqual(self.module2.employee_completed_at, date2)

    def test_none_when_module_not_completed(self):
        """Незавершённый модуль получает None"""
        date1 = timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0))
        completions = {self.module1.id: date1}  # module2 завершён не был

        add_completion_date_each_module(modules=[self.module1, self.module2], completions=completions)

        self.assertEqual(self.module1.employee_completed_at, date1)
        self.assertIsNone(self.module2.employee_completed_at)

    def test_returns_none_and_mutates_in_place(self):
        """Функция меняет модули на месте и возвращает None"""
        completions = {self.module1.id: timezone.now()}

        result = add_completion_date_each_module(modules=[self.module1], completions=completions)

        self.assertIsNone(result)
        self.assertEqual(self.module1.employee_completed_at, completions[self.module1.id])