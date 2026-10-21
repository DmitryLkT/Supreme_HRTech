from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, User

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display=("name",)
    search_fields=("name",)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "department")
    list_filter = (*UserAdmin.list_filter, "department")
    list_select_related = ("department",)

    fieldsets = (*UserAdmin.fieldsets, ("Место работы", {"fields": ("department",)}))
    add_fieldsets = (*UserAdmin.add_fieldsets, ("Место работы", {"fields": ("department",)}))
