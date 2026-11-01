from django.core.exceptions import ValidationError
from django.test import TestCase
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.utils import timezone

from users.models import Department
from ..models import Module, ModuleCompletion, Question, AnswerOption, AnswerSubmission

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

class QuestionModelTest(TestCase):

    def setUp(self):
        """Создание модуля для тестов."""
        self.module = Module.objects.create(
            title="test",
            description="test",
        )

    def test_question_created(self):
        """Создание вопроса."""
        question = Question.objects.create(
            module=self.module,
            text="Как тебя зовут?",
        )

        self.assertIsNotNone(question.pk)

    def test_default_order(self):
        """Значение order по умолчанию."""
        question = Question(
            module=self.module,
            text="Как тебя зовут?",
        )

        self.assertEqual(question.order, 0)

    def test_module_is_required(self):
        """Обязательное поле module."""
        question = Question(
            text="Как тебя зовут?",
        )

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("module", context.exception.message_dict)

    def test_text_is_required(self):
        """Обязательное поле text."""
        question = Question(
            module=self.module,
        )

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("text", context.exception.message_dict)

    def test_order_cannot_be_negative(self):
        """Отрицательный order."""
        question = Question(
            module=self.module,
            text="Как тебя зовут?",
            order=-1,
        )

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("order", context.exception.message_dict)

    def test_str_returns_text(self):
        """Строковое представление."""
        question = Question(
            module=self.module,
            text="Как тебя зовут?",
        )

        self.assertEqual(str(question), "Как тебя зовут?")

    def test_str_truncates_long_text(self):
        """Ограничение строкового представления 80 символами."""
        text = "t" * 100
        question = Question(
            module=self.module,
            text=text,
        )

        self.assertEqual(str(question), text[:80])

    def test_default_ordering(self):
        """Сортировка по order."""
        question1 = Question.objects.create(
            module=self.module,
            text="Первый вопрос",
            order=3,
        )
        question2 = Question.objects.create(
            module=self.module,
            text="Второй вопрос",
            order=1,
        )
        question3 = Question.objects.create(
            module=self.module,
            text="Третий вопрос",
            order=4,
        )
        question4 = Question.objects.create(
            module=self.module,
            text="Четвёртый вопрос",
            order=2,
        )

        questions = [question2, question4, question1, question3]
        qs = list(Question.objects.all())

        self.assertEqual(qs, questions)

    def test_default_ordering_same_order_by_id(self):
        """Сортировка при одинаковом order по id."""
        question1 = Question.objects.create(
            module=self.module,
            text="Первый вопрос",
            order=1,
        )
        question2 = Question.objects.create(
            module=self.module,
            text="Второй вопрос",
            order=1,
        )
        question3 = Question.objects.create(
            module=self.module,
            text="Третий вопрос",
            order=1,
        )

        questions = [question1, question2, question3]
        qs = list(Question.objects.all())

        self.assertEqual(qs, questions)

    def test_related_name_questions(self):
        """Получение вопросов через related_name."""
        question = Question.objects.create(
            module=self.module,
            text="Как тебя зовут?",
        )

        self.assertEqual(list(self.module.questions.all()), [question])

class AnswerOptionModelTest(TestCase):

    def setUp(self):
        """Создание модуля и вопроса для тестов."""
        self.module = Module.objects.create(
            title="test",
            description="test",
        )

        self.question = Question.objects.create(
            module=self.module,
            text="Как тебя зовут?",
        )

    def test_answer_option_created(self):
        """Создание варианта ответа."""
        option = AnswerOption.objects.create(
            question=self.question,
            text="Дмитрий",
        )

        self.assertIsNotNone(option.pk)

    def test_default_is_correct(self):
        """Значение is_correct по умолчанию."""
        option = AnswerOption(
            question=self.question,
            text="Дмитрий",
        )

        self.assertEqual(option.is_correct, False)

    def test_question_is_required(self):
        """Обязательное поле question."""
        option = AnswerOption(
            text="Дмитрий",
        )

        with self.assertRaises(ValidationError) as context:
            option.full_clean()

        self.assertIn("question", context.exception.message_dict)

    def test_text_is_required(self):
        """Обязательное поле text."""
        option = AnswerOption(
            question=self.question,
        )

        with self.assertRaises(ValidationError) as context:
            option.full_clean()

        self.assertIn("text", context.exception.message_dict)

    def test_str_returns_text(self):
        """Строковое представление."""
        option = AnswerOption(
            question=self.question,
            text="Дмитрий",
        )

        self.assertEqual(str(option), "Дмитрий")

    def test_default_ordering(self):
        """Сортировка вариантов ответа по id."""
        option1 = AnswerOption.objects.create(
            question=self.question,
            text="Первый ответ",
        )
        option2 = AnswerOption.objects.create(
            question=self.question,
            text="Второй ответ",
        )
        option3 = AnswerOption.objects.create(
            question=self.question,
            text="Третий ответ",
        )

        options = [option1, option2, option3]
        qs = list(AnswerOption.objects.all())

        self.assertEqual(qs, options)

    def test_related_name_options(self):
        """Получение вариантов ответа через related_name."""
        option = AnswerOption.objects.create(
            question=self.question,
            text="Дмитрий",
        )

        self.assertEqual(
            list(self.question.options.all()),
            [option],
        )

class QuestionIsScoredTest(TestCase):
    """Тестируем свойство Question.is_scored — логика «оценивается ли вопрос»"""

    def setUp(self):
        self.module = Module.objects.create(title="test", description="test")
        self.question = Question.objects.create(module=self.module, text="test?")

    def make_option(self, is_correct):
        return AnswerOption.objects.create(
            question=self.question, text="opt", is_correct=is_correct,
        )

    def test_no_options_is_not_scored(self):
        """Вопрос без вариантов ответа не оценивается"""
        self.assertFalse(self.question.is_scored)

    def test_only_correct_options_is_not_scored(self):
        """Все варианты верные — вопрос «на ценности», не оценивается"""
        self.make_option(is_correct=True)
        self.make_option(is_correct=True)

        self.assertFalse(self.question.is_scored)

    def test_only_incorrect_options_is_not_scored(self):
        """Ни одного верного варианта — не оценивается"""
        self.make_option(is_correct=False)
        self.make_option(is_correct=False)

        self.assertFalse(self.question.is_scored)

    def test_mixed_options_is_scored(self):
        """Есть и верные, и неверные — вопрос оценивается"""
        self.make_option(is_correct=True)
        self.make_option(is_correct=False)

        self.assertTrue(self.question.is_scored)

    def test_single_correct_option_only_is_not_scored(self):
        """Единственный верный вариант без неверных — не оценивается"""
        self.make_option(is_correct=True)

        self.assertFalse(self.question.is_scored)

class AnswerSubmissionModelTest(TestCase):
    def setUp(self):
        """Создание пользователя, модуля, вопроса и вариантов для тестов."""
        self.department = Department.objects.create(name="test")
        self.user = User.objects.create_user(
            username="testuser",
            password="testpassword123",
            department=self.department,
        )
        self.module = Module.objects.create(title="test", description="test")
        self.question = Question.objects.create(module=self.module, text="Как тебя зовут?")
        self.option1 = AnswerOption.objects.create(
            question=self.question, text="Дмитрий", is_correct=True,
        )
        self.option2 = AnswerOption.objects.create(
            question=self.question, text="Не Дмитрий", is_correct=False,
        )

    def test_submission_created(self):
        """Создание ответа."""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1, is_correct=True,
        )

        self.assertIsNotNone(submission.pk)

    def test_default_attempts(self):
        """Значение attempts по умолчанию."""
        submission = AnswerSubmission(
            user=self.user, question=self.question, option=self.option1,
        )

        self.assertEqual(submission.attempts, 1)

    def test_first_answered_at_is_set_automatically(self):
        """Автоматическое заполнение даты первого ответа (auto_now_add)."""
        before = timezone.now()
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )
        after = timezone.now()

        self.assertIsNotNone(submission.first_answered_at)
        self.assertGreaterEqual(submission.first_answered_at, before)
        self.assertLessEqual(submission.first_answered_at, after)

    def test_updated_at_is_set_automatically(self):
        """Автоматическое заполнение даты последнего ответа (auto_now)."""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.assertIsNotNone(submission.updated_at)

    def test_updated_at_changes_on_save(self):
        """auto_now: updated_at обновляется при повторном сохранении"""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )
        original_updated_at = submission.updated_at

        submission.option = self.option2
        submission.save()
        submission.refresh_from_db()

        self.assertGreater(submission.updated_at, original_updated_at)

    def test_first_answered_at_does_not_change_on_save(self):
        """auto_now_add: первая дата остаётся неизменной при повторном сохранении"""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )
        original_first_answered_at = submission.first_answered_at

        submission.option = self.option2
        submission.save()
        submission.refresh_from_db()

        self.assertEqual(submission.first_answered_at, original_first_answered_at)

    def test_user_is_required(self):
        """Обязательное поле user."""
        submission = AnswerSubmission(question=self.question, option=self.option1)

        with self.assertRaises(ValidationError) as context:
            submission.full_clean()

        self.assertIn("user", context.exception.message_dict)

    def test_question_is_required(self):
        """Обязательное поле question."""
        submission = AnswerSubmission(user=self.user, option=self.option1)

        with self.assertRaises(ValidationError) as context:
            submission.full_clean()

        self.assertIn("question", context.exception.message_dict)

    def test_option_is_required(self):
        """Обязательное поле option."""
        submission = AnswerSubmission(user=self.user, question=self.question)

        with self.assertRaises(ValidationError) as context:
            submission.full_clean()

        self.assertIn("option", context.exception.message_dict)

    def test_is_correct_can_be_null(self):
        """is_correct nullable — для вопросов без правильного ответа"""
        submission = AnswerSubmission(
            user=self.user, question=self.question, option=self.option1, is_correct=None,
        )

        submission.full_clean()  # не должно падать

    def test_user_question_combination_must_be_unique(self):
        """Повторный ответ на тот же вопрос тем же сотрудником запрещён на уровне БД"""
        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnswerSubmission.objects.create(
                    user=self.user, question=self.question, option=self.option2,
                )

    def test_same_question_can_be_answered_by_different_users(self):
        """Разные сотрудники могут ответить на один вопрос."""
        another_user = User.objects.create_user(
            username="anotheruser",
            password="testpassword123",
            department=self.department,
        )

        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )
        submission = AnswerSubmission.objects.create(
            user=another_user, question=self.question, option=self.option2,
        )

        self.assertIsNotNone(submission.pk)

    def test_same_user_can_answer_different_questions(self):
        """Один сотрудник может отвечать на разные вопросы."""
        another_question = Question.objects.create(module=self.module, text="Сколько тебе лет?")
        another_option = AnswerOption.objects.create(
            question=another_question, text="Много",
        )

        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )
        submission = AnswerSubmission.objects.create(
            user=self.user, question=another_question, option=another_option,
        )

        self.assertIsNotNone(submission.pk)

    def test_cascade_delete_user(self):
        """Удаление сотрудника удаляет его ответы"""
        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.user.delete()

        self.assertEqual(AnswerSubmission.objects.count(), 0)

    def test_cascade_delete_question(self):
        """Удаление вопроса удаляет ответы на него"""
        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.question.delete()

        self.assertEqual(AnswerSubmission.objects.count(), 0)

    def test_cascade_delete_option(self):
        """Удаление варианта удаляет ответы, где он был выбран"""
        AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.option1.delete()

        self.assertEqual(AnswerSubmission.objects.count(), 0)

    def test_str_returns_user_and_question(self):
        """Строковое представление."""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.assertEqual(str(submission), f"{self.user} - {self.question}")

    def test_related_name_submissions(self):
        """Доступ к ответам через related_name — и у вопроса, и у варианта."""
        submission = AnswerSubmission.objects.create(
            user=self.user, question=self.question, option=self.option1,
        )

        self.assertEqual(list(self.question.submissions.all()), [submission])
        self.assertEqual(list(self.option1.submissions.all()), [submission])