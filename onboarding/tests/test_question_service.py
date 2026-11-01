from django.contrib.auth import get_user_model
from django.http import Http404
from django.test import TestCase

from ..models import AnswerOption, AnswerSubmission, Module, Question
from onboarding.services.question_service import validate_answer_option_id, get_answer_option_question, get_question, check_answer, save_answer_submission
from users.models import Department

User = get_user_model()


class QuestionServiceBase(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="test")
        self.user = User.objects.create_user(
            username="employee", password="testPassword123", department=self.department,
        )
        self.published_module = Module.objects.create(title="m1", description="d", is_published=True)
        self.unpublished_module = Module.objects.create(title="m2", description="d", is_published=False)

        # оцениваемый вопрос: есть и верный, и неверный варианты
        self.scored_question = Question.objects.create(
            module=self.published_module, text="Сколько будет 2+2?",
        )
        self.correct_option = AnswerOption.objects.create(
            question=self.scored_question, text="4", is_correct=True,
        )
        self.wrong_option = AnswerOption.objects.create(
            question=self.scored_question, text="5", is_correct=False,
        )

        # вопрос «на ценности»: все варианты верные
        self.values_question = Question.objects.create(
            module=self.published_module, text="Как ты поступишь?",
        )
        AnswerOption.objects.create(question=self.values_question, text="Хорошо", is_correct=True)
        AnswerOption.objects.create(question=self.values_question, text="Очень хорошо", is_correct=True)


class GetQuestionTest(QuestionServiceBase):
    def test_returns_question_from_published_module(self):
        """Вопрос из опубликованного модуля находится"""
        self.assertEqual(get_question(self.scored_question.id), self.scored_question)

    def test_404_for_question_from_unpublished_module(self):
        """Вопрос из неопубликованного модуля недоступен"""
        question = Question.objects.create(module=self.unpublished_module, text="q?")

        with self.assertRaises(Http404):
            get_question(question.id)

    def test_404_for_missing_question(self):
        """Несуществующий id — Http404"""
        with self.assertRaises(Http404):
            get_question(999999)


class GetAnswerOptionQuestionTest(QuestionServiceBase):
    def test_returns_option_of_question(self):
        """Вариант возвращается по id и вопросу"""
        result = get_answer_option_question(
            question=self.scored_question, option_id=self.correct_option.id,
        )

        self.assertEqual(result, self.correct_option)

    def test_404_for_option_of_other_question(self):
        """Вариант другого вопроса недоступен через этот вопрос (анти-спуфинг)"""
        other_option = AnswerOption.objects.create(
            question=self.values_question, text="x", is_correct=True,
        )

        with self.assertRaises(Http404):
            get_answer_option_question(question=self.scored_question, option_id=other_option.id)

    def test_404_for_missing_option(self):
        """Несуществующий id варианта — Http404"""
        with self.assertRaises(Http404):
            get_answer_option_question(question=self.scored_question, option_id=999999)


class ValidateAnswerOptionIdTest(QuestionServiceBase):
    """Чистая функция — без обращения к БД"""

    def test_none_for_valid_id(self):
        self.assertIsNone(validate_answer_option_id("5"))

    def test_message_for_empty_string(self):
        self.assertEqual(validate_answer_option_id(""), "Выбери вариант ответа.")

    def test_message_for_none(self):
        self.assertEqual(validate_answer_option_id(None), "Выбери вариант ответа.")

    def test_message_for_non_numeric(self):
        self.assertEqual(validate_answer_option_id("abc"), "Выбери вариант ответа.")

    def test_message_for_garbage_suffix(self):
        self.assertEqual(validate_answer_option_id("12a"), "Выбери вариант ответа.")

    def test_message_for_negative_number(self):
        self.assertEqual(validate_answer_option_id("-1"), "Выбери вариант ответа.")

    def test_message_for_float(self):
        self.assertEqual(validate_answer_option_id("1.5"), "Выбери вариант ответа.")

class CheckAnswerTest(QuestionServiceBase):
    def test_correct_answer(self):
        """Верный ответ на оцениваемый вопрос"""
        result = check_answer(question=self.scored_question, selected_option=self.correct_option)

        self.assertTrue(result["scored"])
        self.assertTrue(result["is_correct"])
        self.assertEqual(result["correct_option"], self.correct_option)
        self.assertEqual(result["selected_option"], self.correct_option)
        self.assertEqual(result["message"], "Правильно!")

    def test_wrong_answer_includes_correct_text(self):
        """Неверный ответ: сообщение содержит подсказку с верным вариантом"""
        result = check_answer(question=self.scored_question, selected_option=self.wrong_option)

        self.assertFalse(result["is_correct"])
        self.assertEqual(
            result["message"],
            f"Неверно. Попробуй ещё раз. Правильный ответ: {self.correct_option.text}",
        )

    def test_unscored_question_is_correct_none(self):
        """Вопрос «на ценности»: is_correct = None, специальное сообщение"""
        option = self.values_question.options.first()

        result = check_answer(question=self.values_question, selected_option=option)

        self.assertFalse(result["scored"])
        self.assertIsNone(result["is_correct"])
        self.assertEqual(
            result["message"],
            ("Ответ записан. Здесь нет правильного и неправильного: "
             "важно, как ты поступил бы на самом деле."),
        )

class SaveAnswerSubmissionTest(QuestionServiceBase):
    def test_first_answer_creates_submission(self):
        """Первый ответ создаёт запись с attempts = 1"""
        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.wrong_option, is_correct=False,
        )

        submission = AnswerSubmission.objects.get(user=self.user, question=self.scored_question)
        self.assertEqual(submission.option, self.wrong_option)
        self.assertFalse(submission.is_correct)
        self.assertEqual(submission.attempts, 1)

    def test_retake_updates_submission(self):
        """Повторный ответ обновляет запись, а не создаёт новую; attempts растёт"""
        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.wrong_option, is_correct=False,
        )
        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.correct_option, is_correct=True,
        )

        self.assertEqual(AnswerSubmission.objects.count(), 1)
        submission = AnswerSubmission.objects.get(user=self.user, question=self.scored_question)
        self.assertEqual(submission.option, self.correct_option)
        self.assertTrue(submission.is_correct)
        self.assertEqual(submission.attempts, 2)

    def test_third_attempt(self):
        """Счётчик растёт с каждой попыткой"""
        for _ in range(3):
            save_answer_submission(
                user=self.user, question=self.scored_question,
                selected_option=self.wrong_option, is_correct=False,
            )

        submission = AnswerSubmission.objects.get(user=self.user, question=self.scored_question)
        self.assertEqual(submission.attempts, 3)

    def test_first_answered_at_preserved_on_retake(self):
        """Дата первого ответа не меняется при пересдаче (auto_now_add)"""
        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.wrong_option, is_correct=False,
        )
        first = AnswerSubmission.objects.get(user=self.user, question=self.scored_question)
        original_first_answered_at = first.first_answered_at

        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.correct_option, is_correct=True,
        )
        first.refresh_from_db()

        self.assertEqual(first.first_answered_at, original_first_answered_at)

    def test_updated_at_changes_on_retake(self):
        """Дата последнего ответа обновляется при пересдаче — ЛОВИТ БАГ с update() и auto_now"""
        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.wrong_option, is_correct=False,
        )
        first = AnswerSubmission.objects.get(user=self.user, question=self.scored_question)
        original_updated_at = first.updated_at

        save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.correct_option, is_correct=True,
        )
        first.refresh_from_db()

        self.assertGreater(first.updated_at, original_updated_at)

    def test_returns_none(self):
        """Функция ничего не возвращает"""
        result = save_answer_submission(
            user=self.user, question=self.scored_question,
            selected_option=self.wrong_option, is_correct=False,
        )

        self.assertIsNone(result)

    def test_unscored_submission_is_correct_none(self):
        """Для вопроса без оценки is_correct сохраняется как None"""
        option = self.values_question.options.first()
        save_answer_submission(
            user=self.user, question=self.values_question,
            selected_option=option, is_correct=None,
        )

        submission = AnswerSubmission.objects.get(user=self.user, question=self.values_question)
        self.assertIsNone(submission.is_correct)

