from django.contrib import admin

from .models import Module, AnswerOption, Question

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
