from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from .models import (
    AnswerOption,
    AnswerUser,
    Questionnaire,
    QuestionnaireCompletion,
    QuestionQuestionnaire,
)


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 5
    min_num = 5
    max_num = 5
    validate_min = True
    validate_max = True


class QuestionInline(admin.TabularInline):
    model = QuestionQuestionnaire
    extra = 0
    fields = ("order", "category", "text", "is_required")
    show_change_link = True


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("title", "version", "status", "date_of_creation")
    list_filter = ("status",)
    readonly_fields = ("status",)  # статус меняется только действиями ниже
    inlines = [QuestionInline]
    actions = ["publish_selected", "archive_selected"]

    @admin.action(description="Опубликовать выбранные черновики")
    def publish_selected(self, request, queryset):
        for questionnaire in queryset:
            try:
                questionnaire.publish()
            except ValidationError as error:
                self.message_user(
                    request, f"«{questionnaire}»: {' '.join(error.messages)}",
                    level=messages.ERROR,
                )
            else:
                self.message_user(request, f"«{questionnaire}» опубликована.")

    @admin.action(description="Архивировать выбранные анкеты")
    def archive_selected(self, request, queryset):
        updated = queryset.exclude(status=Questionnaire.Status.ARCHIVED).update(
            status=Questionnaire.Status.ARCHIVED,
        )
        self.message_user(request, f"Архивировано анкет: {updated}.")


@admin.register(QuestionQuestionnaire)
class QuestionQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("text", "questionnaire", "category", "order", "is_required")
    list_filter = ("questionnaire", "category")
    inlines = [AnswerOptionInline]


class AnswerUserInline(admin.TabularInline):
    model = AnswerUser
    extra = 0
    can_delete = False
    readonly_fields = ("question_questionnaire", "answer_option")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuestionnaireCompletion)
class QuestionnaireCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "questionnaire", "week_start", "completed_at")
    list_filter = ("week_start", "questionnaire")
    readonly_fields = ("user", "questionnaire", "week_start", "completed_at", "comment")
    inlines = [AnswerUserInline]

    def has_add_permission(self, request):
        return False
