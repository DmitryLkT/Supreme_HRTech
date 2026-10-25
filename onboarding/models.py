from django.db import models
from django.conf import settings

#Модуль
class Module(models.Model):
    title=models.CharField(max_length=200, verbose_name="Название")
    description=models.TextField(verbose_name="Описание")
    order=models.PositiveIntegerField(default=0, verbose_name="Порядок")
    is_published=models.BooleanField(default=False, verbose_name="Опубликован")
    content=models.TextField(blank=True, default="", verbose_name="Учебный материал")

    class Meta:
        ordering=['order', 'id']
        verbose_name="Модули адаптации"
        verbose_name_plural=verbose_name

    # TODO
    def __str__(self):
        return self.title

#Завершенные модули сотрудником
class ModuleCompletion(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Сотрудник")
    module=models.ForeignKey(Module, on_delete=models.CASCADE, verbose_name="Модуль")
    completed_at=models.DateTimeField(auto_now_add=True, verbose_name="Дата завершения")

    #TODO
    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["user", "module"],
                name="unique_user_module_completion"
            )
        ]

        permissions=[
            ("view_employee_progress", "Может просматривать прогресс всех сотрудников")
        ]

        verbose_name="Завершение модуля"
        verbose_name_plural="Завершение модулей"

    def __str__(self):
        return f"{self.user} - {self.module}"

#Вопросы в модуле
class Question(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="questions", verbose_name="Модуль")
    text=models.TextField(verbose_name="Текст вопроса")
    order=models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        ordering=['order', 'id']
        verbose_name="Вопрос"
        verbose_name_plural="Вопросы"

    def __str__(self):
        return self.text[:80]

    @property
    def is_scored(self):
        """Вопрос с правильным ответом: есть и верные, и неверные варианты.

        Если все варианты помечены верными (или ни один), вопрос на ценности
        и поведение: правильного ответа нет, оценка не выставляется.
        """
        flags = {option.is_correct for option in self.options.all()}
        return flags == {True, False}

#Варианты ответа на вопрос
class AnswerOption(models.Model):
    question=models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options", verbose_name="Вопрос")
    text=models.TextField(max_length=300, verbose_name="Текст ответа")
    is_correct=models.BooleanField(default=False, verbose_name="Правильный ответ")

    class Meta:
        ordering=['id']
        verbose_name="Вариант ответа"
        verbose_name_plural="Варианты ответов"

    def __str__(self):
        return self.text


#Последний ответ сотрудника на вопрос модуля
class AnswerSubmission(models.Model):
    """Последний ответ сотрудника на вопрос модуля.

    Одна запись на пару (сотрудник, вопрос). При повторном ответе запись
    обновляется, а attempts увеличивается.
    """
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Сотрудник"
    )

    question=models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="Вопрос"
    )

    option=models.ForeignKey(
        AnswerOption,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="Выбранный вариант"
    )

    is_correct=models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Верно (пусто для вопросов без правильного ответа)"
    )

    attempts=models.PositiveIntegerField(
        default=1,
        verbose_name="Попыток"
    )

    first_answered_at=models.DateTimeField(
        auto_now_add=True,
        verbose_name="Первый ответ"
    )

    updated_at=models.DateTimeField(
        auto_now=True,
        verbose_name="Последний ответ"
    )

    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["user", "question"],
                name="unique_user_question_submission"
            )
        ]
        verbose_name="Ответ сотрудника на вопрос модуля"
        verbose_name_plural="Ответы сотрудников на вопросы модулей"

    def __str__(self):
        return f"{self.user} - {self.question}"
