from django.contrib import admin

from .models import MentorQuestion, PathProgress, PathStep

@admin.register(PathStep)
class PathStepAdmin(admin.ModelAdmin):
    list_display = ["title", "period", "order", "is_published", "is_placeholder"]
    list_filter = ["period", "is_published", "is_placeholder"]
    search_fields = ["title"]


@admin.register(PathProgress)
class PathProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "step", "done_at"]
    list_filter = ["step__period"]
    search_fields = ["user__username", "step__title"]


@admin.register(MentorQuestion)
class MentorQuestionAdmin(admin.ModelAdmin):
    list_display = ["text", "user", "category", "created_at", "answered_at"]
    list_filter = ["category"]
    search_fields = ["text", "user__username"]