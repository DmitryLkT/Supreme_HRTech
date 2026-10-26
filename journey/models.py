from django.conf import settings
from django.db import models


class PathStep(models.Model):
    """Шаг из плана «Первые 90 дней». Редактируется в админке."""

    class Period(models.IntegerChoices):
        D30 = 30, "Первые 30 дней"
        D60 = 60, "До 60 дней"
        D90 = 90, "До 90 дней"

    period = models.PositiveSmallIntegerField(choices=Period.choices, verbose_name="Период")
    title = models.CharField(max_length=200, verbose_name="Шаг")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_published = models.BooleanField(default=True, verbose_name="Опубликован")
    is_placeholder = models.BooleanField(
        default=False,
        verbose_name="Пример (содержание ещё не утверждено)",
        help_text="Пока отмечено, сотрудник видит пометку, что шаги примерные.",
    )

    class Meta:
        ordering = ["period", "order", "id"]
        verbose_name = "Шаг пути 30/60/90"
        verbose_name_plural = "Шаги пути 30/60/90"

    def __str__(self):
        return f"{self.get_period_display()}: {self.title}"


class PathProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Сотрудник")
    step = models.ForeignKey(PathStep, on_delete=models.CASCADE, related_name="progress", verbose_name="Шаг")
    done_at = models.DateTimeField(auto_now_add=True, verbose_name="Выполнено")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "step"], name="unique_user_path_step"),
        ]
        verbose_name = "Выполнение шага"
        verbose_name_plural = "Выполнение шагов"

    def __str__(self):
        return f"{self.user} - {self.step}"


class MentorQuestion(models.Model):
    class Category(models.TextChoices):
        TASK = "task", "Не понимаю задачу"
        PROCESS = "process", "Процессы и согласования"
        COMMUNICATION = "communication", "Как принято общаться"
        OTHER = "other", "Другое"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="mentor_questions", verbose_name="Сотрудник")
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER, verbose_name="Тема")
    text = models.TextField(max_length=1000, verbose_name="Вопрос")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Задан")
    answer = models.TextField(blank=True, default="", verbose_name="Ответ")
    answered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+", verbose_name="Кто ответил")
    answered_at = models.DateTimeField(null=True, blank=True, verbose_name="Отвечен")

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Вопрос наставнику"
        verbose_name_plural = "Вопросы наставнику"

    @property
    def is_answered(self):
        return bool(self.answer)

    def __str__(self):
        return self.text[:60]
