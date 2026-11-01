import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.test import TestCase
from django.utils import timezone

from ..models import MentorQuestion, PathProgress, PathStep

from users.models import Department

User = get_user_model()


def make_user(username="employee", department=None):
    if department is None:
        department = Department.objects.create(name="test")
    return User.objects.create_user(
        username=username, password="testPassword123", department=department,
    )


def make_step(period=PathStep.Period.D30, title="step", **extra):
    defaults = {"is_published": True, "order": 0}
    defaults.update(extra)
    return PathStep.objects.create(period=period, title=title, **defaults)

class PathStepModelTest(TestCase):
    def test_step_created(self):
        """Создание шага"""
        step = make_step(title="test")

        self.assertIsNotNone(step.pk)

    def test_default_values(self):
        """order=0, is_published=True, is_placeholder=False"""
        step = PathStep(period=PathStep.Period.D30, title="test")

        self.assertEqual(step.order, 0)
        self.assertTrue(step.is_published)
        self.assertFalse(step.is_placeholder)

    def test_period_is_required(self):
        """Обязательное поле period"""
        step = PathStep(title="test")

        with self.assertRaises(ValidationError) as context:
            step.full_clean()

        self.assertIn("period", context.exception.message_dict)

    def test_period_accepts_only_choices(self):
        """period принимает значения 30/60/90"""
        for period in (PathStep.Period.D30, PathStep.Period.D60, PathStep.Period.D90):
            PathStep(period=period, title="test").full_clean()

    def test_period_rejects_unknown_value(self):
        """Значение вне choices не проходит валидацию"""
        step = PathStep(period=45, title="test")

        with self.assertRaises(ValidationError) as context:
            step.full_clean()

        self.assertIn("period", context.exception.message_dict)

    def test_period_cannot_be_negative(self):
        """Отрицательный period не проходит валидацию"""
        step = PathStep(period=-30, title="test")

        with self.assertRaises(ValidationError) as context:
            step.full_clean()

        self.assertIn("period", context.exception.message_dict)

    def test_title_is_required(self):
        """Обязательное поле title"""
        step = PathStep(period=PathStep.Period.D30)

        with self.assertRaises(ValidationError) as context:
            step.full_clean()

        self.assertIn("title", context.exception.message_dict)

    def test_title_max_length(self):
        """Ограничение длины title — 200 символов (CharField проверяется в full_clean)"""
        step = PathStep(period=PathStep.Period.D30, title="t" * 201)

        with self.assertRaises(ValidationError):
            step.full_clean()

    def test_order_cannot_be_negative(self):
        """Отрицательный order"""
        step = PathStep(period=PathStep.Period.D30, title="test", order=-1)

        with self.assertRaises(ValidationError) as context:
            step.full_clean()

        self.assertIn("order", context.exception.message_dict)

    def test_str_returns_period_display_and_title(self):
        """«Человеческий» период + название"""
        step = PathStep(period=PathStep.Period.D60, title="Познакомиться с командой")

        self.assertEqual(str(step), "До 60 дней: Познакомиться с командой")

    def test_default_ordering(self):
        """Сортировка по (period, order, id)"""
        d90 = make_step(period=PathStep.Period.D90, title="d90", order=1)
        d30_second = make_step(period=PathStep.Period.D30, title="d30-2", order=2)
        d60 = make_step(period=PathStep.Period.D60, title="d60", order=1)
        d30_first = make_step(period=PathStep.Period.D30, title="d30-1", order=1)

        qs = list(PathStep.objects.all())

        self.assertEqual(qs, [d30_first, d30_second, d60, d90])

    def test_default_ordering_same_period_and_order_by_id(self):
        """При равных period и order порядок определяется id"""
        first = make_step(title="a", order=1)
        second = make_step(title="b", order=1)
        third = make_step(title="c", order=1)

        self.assertEqual(list(PathStep.objects.all()), [first, second, third])

    def test_ordering_ignores_creation_order(self):
        """Порядок определяется полями, а не порядком создания"""
        created_late = make_step(period=PathStep.Period.D90, title="later", order=1)
        created_early = make_step(period=PathStep.Period.D30, title="earlier", order=5)

        self.assertEqual(list(PathStep.objects.all()), [created_early, created_late])

    def test_period_choices_values(self):
        """Значения IntegerChoices — 30/60/90"""
        self.assertEqual(PathStep.Period.D30.value, 30)
        self.assertEqual(PathStep.Period.D60.value, 60)
        self.assertEqual(PathStep.Period.D90.value, 90)
        self.assertEqual([c[0] for c in PathStep.Period.choices], [30, 60, 90])

    def test_placeholder_flag_can_be_set(self):
        """Флаг «пример» сохраняется и читается"""
        step = make_step(title="test", is_placeholder=True)

        step.refresh_from_db()
        self.assertTrue(step.is_placeholder)

    def test_placeholder_default_is_false(self):
        """По умолчанию шаг не помечен как пример"""
        step = make_step(title="test")

        step.refresh_from_db()
        self.assertFalse(step.is_placeholder)

class PathProgressModelTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="test")
        self.user = make_user("testuser", self.department)
        self.step = make_step()

    def test_progress_created(self):
        """Создание записи о выполнении шага"""
        progress = PathProgress.objects.create(user=self.user, step=self.step)

        self.assertIsNotNone(progress.pk)

    def test_done_at_is_set_automatically(self):
        """done_at заполняется автоматически (auto_now_add)"""
        before = timezone.now()
        progress = PathProgress.objects.create(user=self.user, step=self.step)
        after = timezone.now()

        self.assertGreaterEqual(progress.done_at, before)
        self.assertLessEqual(progress.done_at, after)

    def test_done_at_does_not_change_on_save(self):
        """auto_now_add: дата выполнения не меняется при повторном сохранении"""
        progress = PathProgress.objects.create(user=self.user, step=self.step)
        original = progress.done_at

        progress.save()
        progress.refresh_from_db()

        self.assertEqual(progress.done_at, original)

    def test_user_is_required(self):
        """Обязательное поле user"""
        progress = PathProgress(step=self.step)

        with self.assertRaises(ValidationError) as context:
            progress.full_clean()

        self.assertIn("user", context.exception.message_dict)

    def test_step_is_required(self):
        """Обязательное поле step"""
        progress = PathProgress(user=self.user)

        with self.assertRaises(ValidationError) as context:
            progress.full_clean()

        self.assertIn("step", context.exception.message_dict)

    def test_user_step_combination_must_be_unique(self):
        """Повторное выполнение шага тем же сотрудником запрещено на уровне БД"""
        PathProgress.objects.create(user=self.user, step=self.step)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PathProgress.objects.create(user=self.user, step=self.step)

    def test_same_step_can_be_done_by_different_users(self):
        """Разные сотрудники могут выполнить один шаг"""
        another_user = make_user("another", self.department)

        PathProgress.objects.create(user=self.user, step=self.step)
        progress = PathProgress.objects.create(user=another_user, step=self.step)

        self.assertIsNotNone(progress.pk)

    def test_same_user_can_done_different_steps(self):
        """Один сотрудник может выполнить разные шаги"""
        another_step = make_step(period=PathStep.Period.D60, title="another")

        PathProgress.objects.create(user=self.user, step=self.step)
        progress = PathProgress.objects.create(user=self.user, step=another_step)

        self.assertIsNotNone(progress.pk)

    def test_cascade_delete_user(self):
        """Удаление сотрудника удаляет его выполнения"""
        PathProgress.objects.create(user=self.user, step=self.step)

        self.user.delete()

        self.assertEqual(PathProgress.objects.count(), 0)

    def test_cascade_delete_step(self):
        """Удаление шага удаляет связанные выполнения"""
        PathProgress.objects.create(user=self.user, step=self.step)

        self.step.delete()

        self.assertEqual(PathProgress.objects.count(), 0)

    def test_str_returns_user_and_step(self):
        """Строковое представление"""
        progress = PathProgress.objects.create(user=self.user, step=self.step)

        self.assertEqual(str(progress), f"{self.user} - {self.step}")

    def test_related_name_progress(self):
        """Обратная связь step.progress работает"""
        progress = PathProgress.objects.create(user=self.user, step=self.step)

        self.assertEqual(list(self.step.progress.all()), [progress])

class MentorQuestionModelTest(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="test")
        self.user = make_user("testuser", self.department)

    def test_question_created(self):
        """Создание вопроса наставнику"""
        question = MentorQuestion.objects.create(user=self.user, text="Как получить доступ к Git?")

        self.assertIsNotNone(question.pk)

    def test_default_category_is_other(self):
        """Категория по умолчанию — «Другое»"""
        question = MentorQuestion(user=self.user, text="?")

        self.assertEqual(question.category, MentorQuestion.Category.OTHER)
        self.assertEqual(question.category, "other")

    def test_default_answer_is_empty(self):
        """Ответ по умолчанию пустой"""
        question = MentorQuestion(user=self.user, text="?")

        self.assertEqual(question.answer, "")

    def test_created_at_is_set_automatically(self):
        """created_at заполняется автоматически"""
        before = timezone.now()
        question = MentorQuestion.objects.create(user=self.user, text="?")
        after = timezone.now()

        self.assertGreaterEqual(question.created_at, before)
        self.assertLessEqual(question.created_at, after)

    def test_user_is_required(self):
        """Обязательное поле user"""
        question = MentorQuestion(text="?")

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("user", context.exception.message_dict)

    def test_text_is_required(self):
        """Обязательное поле text"""
        question = MentorQuestion(user=self.user)

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("text", context.exception.message_dict)

    def test_text_length_not_enforced_by_full_clean(self):
        """ОСОБЕННОСТЬ Django: у TextField max_length НЕ проверяется в full_clean — валидатора нет"""
        question = MentorQuestion(user=self.user, text="t" * 1001)

        field = MentorQuestion._meta.get_field("text")
        self.assertEqual(field.max_length, 1000)
        self.assertEqual(field.validators, [])

        question.full_clean()  # не падает: ограничение живёт только на уровне формы

    def test_text_max_length_enforced_by_model_form(self):
        """Ограничение 1000 символов работает через ModelForm (админка) — там и живёт проверка"""
        form_class = modelform_factory(MentorQuestion, fields=["text", "user"])
        form = form_class(data={"text": "t" * 1001, "user": self.user.pk})

        self.assertFalse(form.is_valid())
        self.assertIn("text", form.errors)

    def test_text_at_max_length_is_valid(self):
        """Ровно 1000 символов — допустимо"""
        MentorQuestion(user=self.user, text="t" * 1000).full_clean()

    def test_invalid_category_rejected(self):
        """Недопустимая категория не проходит валидацию"""
        question = MentorQuestion(user=self.user, text="?", category="unknown")

        with self.assertRaises(ValidationError) as context:
            question.full_clean()

        self.assertIn("category", context.exception.message_dict)

    def test_all_categories_are_valid(self):
        """Все объявленные категории проходят валидацию"""
        for category in MentorQuestion.Category:
            MentorQuestion(user=self.user, text="?", category=category).full_clean()

    def test_category_choices_values(self):
        """Значения категорий соответствуют объявленным"""
        self.assertEqual(
            [c[0] for c in MentorQuestion.Category.choices],
            ["task", "process", "communication", "other"],
        )

    def test_is_answered_false_without_answer(self):
        """Без ответа is_answered = False"""
        question = MentorQuestion.objects.create(user=self.user, text="?")

        self.assertFalse(question.is_answered)

    def test_is_answered_true_with_answer(self):
        """С текстом ответа is_answered = True"""
        question = MentorQuestion.objects.create(user=self.user, text="?", answer="Смотри в вики")

        self.assertTrue(question.is_answered)

    def test_is_answered_ignores_answered_at(self):
        """is_answered смотрит только на текст ответа, а не на дату"""
        question = MentorQuestion.objects.create(user=self.user, text="?", answered_at=timezone.now())

        self.assertFalse(question.is_answered)

    def test_is_answered_with_whitespace_only_answer(self):
        """Пробельный ответ считается ответом — bool(' ') == True"""
        question = MentorQuestion.objects.create(user=self.user, text="?", answer="   ")

        self.assertTrue(question.is_answered)

    def test_str_truncates_to_60(self):
        """Строковое представление обрезается до 60 символов"""
        question = MentorQuestion(user=self.user, text="t" * 100)

        self.assertEqual(str(question), "t" * 60)

    def test_str_short_text_unchanged(self):
        """Короткий текст выводится полностью"""
        question = MentorQuestion(user=self.user, text="Короткий вопрос")

        self.assertEqual(str(question), "Короткий вопрос")

    def test_default_ordering_newest_first(self):
        """Сортировка: сначала новые (created_at desc)"""
        old = MentorQuestion.objects.create(user=self.user, text="old")
        new = MentorQuestion.objects.create(user=self.user, text="new")
        # даты задаём явно: auto_now_add у записей подряд может совпасть
        MentorQuestion.objects.filter(pk=old.pk).update(
            created_at=timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0))
        )
        MentorQuestion.objects.filter(pk=new.pk).update(
            created_at=timezone.make_aware(datetime.datetime(2026, 6, 1, 10, 0))
        )

        self.assertEqual(list(MentorQuestion.objects.all()), [new, old])

    def test_ordering_same_created_at_by_id_desc(self):
        """При одинаковом created_at порядок — по убыванию id"""
        first = MentorQuestion.objects.create(user=self.user, text="first")
        second = MentorQuestion.objects.create(user=self.user, text="second")
        third = MentorQuestion.objects.create(user=self.user, text="third")
        same_moment = timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0))
        MentorQuestion.objects.filter(pk__in=[first.pk, second.pk, third.pk]).update(
            created_at=same_moment
        )

        self.assertEqual(list(MentorQuestion.objects.all()), [third, second, first])

    def test_answered_by_is_nullable(self):
        """answered_by может быть пустым"""
        question = MentorQuestion.objects.create(user=self.user, text="?")

        self.assertIsNone(question.answered_by)

    def test_answered_by_set_null_on_mentor_delete(self):
        """Удаление наставника обнуляет answered_by, но вопрос остаётся"""
        mentor = make_user("mentor", self.department)
        question = MentorQuestion.objects.create(
            user=self.user, text="?", answer="ответ", answered_by=mentor,
            answered_at=timezone.now(),
        )

        mentor.delete()
        question.refresh_from_db()

        self.assertIsNone(question.answered_by)
        self.assertTrue(MentorQuestion.objects.filter(pk=question.pk).exists())

    def test_cascade_delete_user(self):
        """Удаление сотрудника удаляет его вопросы"""
        MentorQuestion.objects.create(user=self.user, text="?")

        self.user.delete()

        self.assertEqual(MentorQuestion.objects.count(), 0)

    def test_related_name_mentor_questions(self):
        """Обратная связь user.mentor_questions работает"""
        question = MentorQuestion.objects.create(user=self.user, text="?")

        self.assertEqual(list(self.user.mentor_questions.all()), [question])

    def test_answered_at_can_be_empty(self):
        """answered_at nullable"""
        question = MentorQuestion.objects.create(user=self.user, text="?")

        self.assertIsNone(question.answered_at)