from django.contrib import admin, messages
from .models import Questionnaire, QuestionnaireVersion
from .services.publication import set_publication


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title", "code")
    ordering = ("title",)

    readonly_fields = ("code", "title", "description", "is_published")

    actions = ("publish_selected", "unpublish_selected")

    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Опубликовать выбранные анкеты", permissions=["change"])
    def publish_selected(self, request, queryset):
        self._set_publication(request, queryset, True)

    @admin.action(description="Снять выбранные анкеты с публикации", permissions=["change"])
    def unpublish_selected(self, request, queryset):
        self._set_publication(request, queryset, False)

    def _set_publication(self, request, queryset, is_published):
        questionnaire_ids = list(queryset.values_list("pk", flat=True))

        try:
            changed_count = set_publication(questionnaire_ids=questionnaire_ids, is_published=is_published)
        except ValueError as error:
            self.message_user(request, " ".join(error.messages), level=messages.ERROR)
            return

        self.message_user(
            request,
            f"Количество изменённых анкет: {changed_count}.",
            level=messages.SUCCESS,)

    @admin.register(QuestionnaireVersion)
    class QuestionnaireVersionAdmin(admin.ModelAdmin):
        list_display = ("questionnaire", "version", "created_at")
        list_filter = ("questionnaire",)
        search_fields = ("questionnaire__title", "questionnaire__code", "version")
        list_select_related = ("questionnaire",)
        ordering = ("questionnaire", "-created_at")

        readonly_fields = ("questionnaire", "version", "definition", "created_at")

        def has_add_permission(self, request):
            return False
        def has_delete_permission(self, request, obj=None):
            return False
        def has_change_permission(self, request, obj=None):
            return False