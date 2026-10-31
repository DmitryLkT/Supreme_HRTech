from django.contrib import admin

from .models import Module, AnswerOption, Question, AnswerSubmission

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display=("title", "order", "is_published")
    list_filter=("is_published",)
    search_fields=("title", "description")

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 3

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display=("text", "module", "order")
    list_filter=("module",)
    search_fields=("text",)
    inlines=(AnswerOptionInline,)


@admin.register(AnswerSubmission)
class AnswerSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "question", "option", "is_correct", "attempts", "updated_at")
    list_filter = ("is_correct", "question__module")
    search_fields = ("user__username", "question__text")
    readonly_fields = [f.name for f in AnswerSubmission._meta.fields]

    def has_add_permission(self, request):
        return False
