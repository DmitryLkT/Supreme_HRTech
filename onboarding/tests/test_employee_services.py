from django.test import TestCase
from django.contrib.auth import get_user_model

from onboarding.services.employee_services import get_employees_queryset, filtering_employees_words

from users.models import Department

User = get_user_model()

class FilteringEmployeesWordsTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            name="testDepartment",
        )

        self.user1 = User.objects.create_user(
            username="testUser1",
            first_name="testFirstName1",
            last_name="testLastName1",
            password="testPassword123",
            department=self.department,
        )
        self.user2 = User.objects.create_user(
            username="testUser2",
            first_name="testFirstName2",
            last_name="testLastName2",
            password="testPassword321",
            department=self.department,
        )
        self.user3 = User.objects.create_user(
            username="testUser3",
            first_name="testFirstName3",
            last_name="testLastName3",
            password="testPassword3211",
            department=self.department,
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