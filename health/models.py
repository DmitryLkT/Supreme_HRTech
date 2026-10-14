from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

# Анкета
class Questionnaire(models.Model):
    class Status(models.TextChoices):
        DRAFT="draft"
        ACTIVE="active"
        ARCHIVED="archived"

    title=models.CharField(max_length=100, verbose_name="Название")
    description=models.TextField(verbose_name="Описание")
    status=models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, verbose_name="Статус")
    version=models.PositiveIntegerField(default=1, verbose_name="Версия")
    date_of_creation=models.DateField(default=timezone.localdate, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Анкета"
        verbose_name_plural = "Анкеты"

        constraints = [
            models.UniqueConstraint(fields=["status"],
                                    condition=models.Q(status="active"),
                                    name="unique_status"),
        ]

    def publish(self):
        if self.pk is None:
            raise ValidationError("Сначало сохраниет черновик анкеты.")
        if self.status != self.Status.DRAFT:
            raise ValidationError("Можно пуюликолвать только черновики.")

        with transaction.atomic():
            another_active = type(self).objects.filter(
                status=self.Status.ACTIVE
            ).exclude(pk=self.pk).exists()

            if another_active:
                raise ValidationError(
                    "Сначала архивируйте текущую активную анкету."
                )

            questions = self.questionquestionnaire_set.all()

            if not questions.exists():
                raise ValidationError(
                    "Нельзя опубликовать анкету без вопросов."
                )

            for question in questions:
                scores = list(
                    question.answeroption_set.values_list("score", flat=True)
                )

                if len(scores) != 5 or set(scores) != {1, 2, 3, 4, 5}:
                    raise ValidationError(
                        f"У вопроса «{question.text}» "
                        "должно быть ровно пять вариантов "
                        "с оценками от 1 до 5."
                    )

            self.status = self.Status.ACTIVE
            self.save(update_fields=["status"])

    def __str__(self):
        return self.title

# Вопрос в анкете
class QuestionQuestionnaire(models.Model):
    questionnaire=models.ForeignKey(Questionnaire, on_delete=models.CASCADE, verbose_name="Анкета")
    text=models.TextField(verbose_name="Текст вопроса")
    order=models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_required=models.BooleanField(default=True, verbose_name="Обязательность")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text

# Варианты ответа
class AnswerOption(models.Model):
    question=models.ForeignKey(QuestionQuestionnaire, on_delete=models.CASCADE, verbose_name="Вопрос")
    text=models.TextField(max_length=200, verbose_name="Текст ответа")
    order=models.PositiveIntegerField(default=0, verbose_name="Порядок")
    score=models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Оценка")

    class Meta:
        ordering = ["score"]
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"

        constraints = [
            # Оценка должна быть от 1 до 5
            models.CheckConstraint(
                condition=Q(score__gte=1) & Q(score__lte=5),
                name="answer_score_between_1_and_5",
            ),
            # В пределах одного вопроса оценки не повторяются
            models.UniqueConstraint(
                fields=["question", "score"],
                name="unique_score_per_question",
            ),
        ]

    def __str__(self):
        return self.text

# Завершение анкеты
class QuestionnaireCompletion(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Сотрудник")
    questionnaire=models.ForeignKey(Questionnaire, on_delete=models.PROTECT, verbose_name="Анкета")
    completed_at=models.DateTimeField(auto_now_add=True, verbose_name="Дата завершения")
    week_start=models.DateField(verbose_name="Начало недели")

    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["user", "week_start"],
                name="unique_questionnaire_week")
        ]

        verbose_name="Завершение анкеты"
        verbose_name_plural = "Завершение анкет"

    def __str__(self):
        return f"{self.user} - {self.questionnaire} - {self.week_start}"

# Варианты ответа сотрудника
class AnswerUser(models.Model):
    questionnaire_completion=models.ForeignKey(QuestionnaireCompletion, on_delete=models.CASCADE)
    question_questionnaire=models.ForeignKey(QuestionQuestionnaire, on_delete=models.PROTECT)
    answer_option=models.ForeignKey(AnswerOption, on_delete=models.PROTECT)

    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["questionnaire_completion", "question_questionnaire"],
                name="unique_answer_user"
            )
        ]
        verbose_name="Ответ сотрудника"
        verbose_name_plural="Ответы сотрудника"

    def clean(self):
        super().clean()
        errors={}

        if self.questionnaire_completion_id and self.question_questionnaire_id :
            complete_question_id = self.questionnaire_completion.questionnaire_id
            question_questionnaire_id = self.question_questionnaire.questionnaire_id

            if question_questionnaire_id != complete_question_id:
                errors["question_questionnaire"] = "Этот вопрос не принадлежит выбранной анкете"

        if self.question_questionnaire_id and self.answer_option_id:
            if self.answer_option.question_id != self.question_questionnaire_id:
                errors["answer_option"] = "Этот вариант ответа не принадлежит выбранному вопросу."

        if errors:
            raise ValidationError(errors)