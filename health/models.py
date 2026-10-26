from django.db import models
from django.conf import settings


# Анкета
class Questionnaire(models.Model):
    code=models.SlugField(max_length=100, unique=True, verbose_name="Код анкеты")
    title=models.CharField(max_length=100, verbose_name="Название")
    description=models.TextField(verbose_name="Описание")
    is_published = models.BooleanField(default=False, verbose_name="Опубликован")

    class Meta:
        verbose_name = "Анкета"
        verbose_name_plural = "Анкеты"

    def __str__(self):
        return self.title

#версия содержания анкеты
class QuestionnaireVersion(models.Model):
    questionnaire=models.ForeignKey(Questionnaire, on_delete=models.PROTECT, related_name="versions", verbose_name="Анкета")
    version=models.CharField(max_length=20, verbose_name="Версия анкеты")
    definition=models.JSONField(default=dict, verbose_name="Содержание анкеты")
    created_at=models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Версия анкеты"
        verbose_name_plural = "Версии анкет"
        constraints = [
            models.UniqueConstraint(
                fields=["questionnaire", "version"],
                name="unique_questionnaire_version",
            ),
        ]

    def __str__(self):
        return f"{self.questionnaire.title} — {self.version}"

#факт прохождения анкеты
class Submission(models.Model):
    employee=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="wellbeing_submissions", verbose_name="Сотрудник")
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.PROTECT, related_name="submissions", verbose_name="Анкета")
    version_quest=models.ForeignKey(QuestionnaireVersion, on_delete=models.PROTECT, related_name="submissions", verbose_name="Версия анкеты")
    department=models.CharField(max_length=150, unique=False, verbose_name="Название отдела")
    week_start=models.DateField(verbose_name="Время заполнения")
    evaluated_week_start=models.DateField(verbose_name="Веремя оцениваемой недели")
    submitted_at=models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    expires_at=models.DateField(verbose_name="Время удаления")

    class Meta:
        verbose_name = "Прохождение анкеты"
        verbose_name_plural = "Прохождения анкет"
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "questionnaire", "week_start"],
                name="unique_employee_questionnaire_week",
            ),
        ]

    def __str__(self):
        return f"Прохождение №{self.pk}"

# ответ на вопрос
class Answer(models.Model):
    submission=models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="answers", verbose_name="связь с прохождением")
    question_code=models.CharField(max_length=100, verbose_name="Код вопроса")
    value=models.PositiveSmallIntegerField(verbose_name="Оценка")

    class Meta:
        verbose_name = "Ответ"
        verbose_name_plural = "Ответы"
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question_code"],
                name="unique_submission_question",
            ),
            models.CheckConstraint(
                condition=models.Q(value__gte=1, value__lte=5),
                name="answer_value_between_1_and_5",
            ),
        ]

    def __str__(self):
        return f"{self.question_code}: {self.value}"