from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from ..models import AnswerOption, AnswerSubmission, Module, ModuleCompletion, Question
from onboarding.services.progress_services import (
    get_answers_count_by_options,
    get_last_answer_progress,
    get_user_module_progress,
)

from users.models import Department

User = get_user_model()


class ProgressServicesBase(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="test")
        self.user = User.objects.create_user(
            username="employee", password="testPassword123", department=self.department,
        )
        self.module1 = Module.objects.create(title="m1", description="d", is_published=True, order=1)
        self.module2 = Module.objects.create(title="m2", description="d", is_published=True, order=2)
        self.unpublished = Module.objects.create(title="u", description="d", is_published=False, order=3)

    def make_question_with_options(self, module, n_options=2):
        question = Question.objects.create(module=module, text=f"q {module.title}?")
        options = [
            AnswerOption.objects.create(
                question=question, text=f"opt{i}", is_correct=(i == 0),
            )
            for i in range(n_options)
        ]
        return question, options

class GetUserModuleProgressTest(ProgressServicesBase):
    def test_no_modules(self):
        """Нет опубликованных модулей: нули, percent = 0, next = None"""
        Module.objects.filter(is_published=True).update(is_published=False)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["total_modules"], 0)
        self.assertEqual(result["completed_count"], 0)
        self.assertEqual(result["progress_percent"], 0)
        self.assertIsNone(result["next_module"])
        self.assertEqual(result["modules"], [])
        self.assertEqual(result["completed_module_ids"], set())

    def test_nothing_completed(self):
        """Модули есть, сотрудник ничего не прошёл"""
        result = get_user_module_progress(self.user)

        self.assertEqual(result["total_modules"], 2)
        self.assertEqual(result["completed_count"], 0)
        self.assertEqual(result["progress_percent"], 0)
        self.assertEqual(result["completed_module_ids"], set())
        self.assertEqual(result["next_module"], self.module1)

    def test_all_completed(self):
        """Все модули пройдены: 100%, next = None"""
        ModuleCompletion.objects.create(user=self.user, module=self.module1)
        ModuleCompletion.objects.create(user=self.user, module=self.module2)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["completed_count"], 2)
        self.assertEqual(result["progress_percent"], 100)
        self.assertEqual(result["completed_module_ids"], {self.module1.id, self.module2.id})
        self.assertIsNone(result["next_module"])

    def test_partial_completion_percent(self):
        """1 из 2 = 50%"""
        ModuleCompletion.objects.create(user=self.user, module=self.module1)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["completed_count"], 1)
        self.assertEqual(result["progress_percent"], 50)

    def test_percent_rounding(self):
        """1 из 3 = 33, 2 из 3 = 67 (round)"""
        Module.objects.create(title="m3", description="d", is_published=True, order=3)
        ModuleCompletion.objects.create(user=self.user, module=self.module1)

        self.assertEqual(get_user_module_progress(self.user)["progress_percent"], 33)

        ModuleCompletion.objects.create(user=self.user, module=self.module2)
        self.assertEqual(get_user_module_progress(self.user)["progress_percent"], 67)

    def test_next_module_is_first_uncompleted(self):
        """next_module — первый непройденный по порядку"""
        ModuleCompletion.objects.create(user=self.user, module=self.module1)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["next_module"], self.module2)

    def test_next_module_skips_completed_in_middle(self):
        """Пройден второй по порядку — next всё равно первый непройденный"""
        ModuleCompletion.objects.create(user=self.user, module=self.module2)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["next_module"], self.module1)

    def test_unpublished_completions_do_not_count(self):
        """Прохождение неопубликованного модуля не влияет на прогресс"""
        ModuleCompletion.objects.create(user=self.user, module=self.unpublished)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["completed_count"], 0)
        self.assertEqual(result["completed_module_ids"], set())
        self.assertEqual(result["next_module"], self.module1)

    def test_modules_ordered_by_order_and_id(self):
        """Список модулей упорядочен по (order, id)"""
        result = get_user_module_progress(self.user)

        self.assertEqual(result["modules"], [self.module1, self.module2])

    def test_other_users_completions_do_not_count(self):
        """Чужие прохождения не влияют на прогресс сотрудника"""
        other = User.objects.create_user(
            username="other", password="testPassword123", department=self.department,
        )
        ModuleCompletion.objects.create(user=other, module=self.module1)
        ModuleCompletion.objects.create(user=other, module=self.module2)

        result = get_user_module_progress(self.user)

        self.assertEqual(result["completed_count"], 0)

class GetLastAnswerProgressTest(ProgressServicesBase):
    def test_empty_for_user_without_answers(self):
        """Нет ответов — пустой queryset"""
        self.assertFalse(get_last_answer_progress(self.user).exists())

    def test_returns_user_submissions(self):
        """Возвращаются ответы сотрудника"""
        question, options = self.make_question_with_options(self.module1)
        submission = AnswerSubmission.objects.create(
            user=self.user, question=question, option=options[0],
        )

        result = get_last_answer_progress(self.user)

        self.assertEqual(list(result), [submission])

    def test_excludes_unpublished_modules(self):
        """Ответы на вопросы неопубликованных модулей не попадают в выдачу"""
        question, options = self.make_question_with_options(self.unpublished)
        AnswerSubmission.objects.create(user=self.user, question=question, option=options[0])

        result = get_last_answer_progress(self.user)

        self.assertFalse(result.exists())

    def test_excludes_other_users(self):
        """Чужие ответы не попадают в выдачу"""
        other = User.objects.create_user(
            username="other", password="testPassword123", department=self.department,
        )
        question, options = self.make_question_with_options(self.module1)
        AnswerSubmission.objects.create(user=other, question=question, option=options[0])

        result = get_last_answer_progress(self.user)

        self.assertFalse(result.exists())

    def test_publication_state_changes_visibility(self):
        """Снятие модуля с публикации убирает его ответы из выдачи"""
        question, options = self.make_question_with_options(self.module1)
        AnswerSubmission.objects.create(user=self.user, question=question, option=options[0])
        self.assertTrue(get_last_answer_progress(self.user).exists())

        self.module1.is_published = False
        self.module1.save()

        self.assertFalse(get_last_answer_progress(self.user).exists())

class GetAnswersCountByOptionsTest(ProgressServicesBase):
    def setUp(self):
        super().setUp()
        self.question1, self.options1 = self.make_question_with_options(self.module1)
        self.question2, self.options2 = self.make_question_with_options(self.module2)
        self.question_unpub, self.options_unpub = self.make_question_with_options(
            self.unpublished, n_options=1
        )

    def submit(self, user, option, question):
        AnswerSubmission.objects.create(user=user, question=question, option=option)

    def test_empty_dict_without_answers(self):
        """Без ответов — пустой словарь"""
        self.assertEqual(get_answers_count_by_options(None), {})

    def test_counts_per_option(self):
        """Ответы разных сотрудников на один вариант суммируются"""
        other = User.objects.create_user(
            username="other", password="testPassword123", department=self.department,
        )
        self.submit(self.user, self.options1[0], self.question1)
        self.submit(other, self.options1[0], self.question1)
        self.submit(other, self.options2[0], self.question2)

        counts = get_answers_count_by_options(None)

        self.assertEqual(counts, {
            self.options1[0].id: 2,
            self.options2[0].id: 1,
        })

    def test_counts_across_modules(self):
        """Без фильтра по модулю считаются все опубликованные модули"""
        self.submit(self.user, self.options1[0], self.question1)
        self.submit(self.user, self.options2[0], self.question2)

        counts = get_answers_count_by_options(None)

        self.assertEqual(counts, {
            self.options1[0].id: 1,
            self.options2[0].id: 1,
        })

    def test_filters_by_module(self):
        """module ограничивает подсчёт своим модулем"""
        self.submit(self.user, self.options1[0], self.question1)
        self.submit(self.user, self.options2[0], self.question2)

        counts = get_answers_count_by_options(self.module1)

        self.assertEqual(counts, {self.options1[0].id: 1})

    def test_excludes_unpublished_modules(self):
        """Ответы на вопросы неопубликованных модулей не считаются"""
        self.submit(self.user, self.options_unpub[0], self.question_unpub)

        self.assertEqual(get_answers_count_by_options(None), {})

    def test_excludes_non_employees(self):
        """Ответы суперпользователя и HR не попадают в подсчёт"""
        superuser = User.objects.create_user(
            username="boss", password="testPassword123",
            department=self.department, is_superuser=True,
        )
        hr_group = Group.objects.create(name="HR")
        hr = User.objects.create_user(
            username="hr", password="testPassword123", department=self.department,
        )
        hr.groups.add(hr_group)

        self.submit(superuser, self.options1[0], self.question1)
        self.submit(hr, self.options1[1], self.question1)

        self.assertEqual(get_answers_count_by_options(None), {})

    def test_employees_answers_are_counted(self):
        """Ответы обычных сотрудников считаются"""
        other_employee = User.objects.create_user(
            username="employee2", password="testPassword123", department=self.department,
        )
        self.submit(self.user, self.options1[0], self.question1)
        self.submit(other_employee, self.options1[1], self.question1)

        counts = get_answers_count_by_options(None)

        self.assertEqual(counts, {
            self.options1[0].id: 1,
            self.options1[1].id: 1,
        })

    def test_inactive_employee_excluded(self):
        """Ответы деактивированного сотрудника не считаются"""
        self.user.is_active = False
        self.user.save()
        self.submit(self.user, self.options1[0], self.question1)

        self.assertEqual(get_answers_count_by_options(None), {})

    def test_zero_answers_options_not_in_dict(self):
        """Варианты без ответов отсутствуют в словаре — это важно для consumers"""
        self.submit(self.user, self.options1[0], self.question1)

        counts = get_answers_count_by_options(None)

        self.assertNotIn(self.options1[1].id, counts)
        self.assertEqual(counts, {self.options1[0].id: 1})

    def test_module_filter_with_unpublished_module(self):
        """Фильтр по неопубликованному модулю даёт пустой словарь"""
        self.submit(self.user, self.options_unpub[0], self.question_unpub)

        self.assertEqual(get_answers_count_by_options(self.unpublished), {})