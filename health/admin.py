from django.contrib import admin
from .models import AnswerOption

class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 5
    min_num = 5
    max_num = 5
    validate_min = True
    validate_max = True