from django.db.models import Count, Max, Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

def filtering_employees_words(*, query, employees):
    """Фильтрует сотрудников по логину, имени и фамилии"""
    for word in query.split():
        employees = employees.filter(
            Q(username__icontains=word) | Q(first_name__icontains=word)
            | Q(last_name__icontains=word)
        )

    return employees

def get_employees_queryset():
    """Получает сотрудников и добавляет каждому два вычисляемых поля"""
    published = Q(modulecompletion__module__is_published=True)
    employees = _employees_queryset().annotate(
        completed_count=Count("modulecompletion__module_id", filter=published, distinct=True),
        last_completed_at=Max("modulecompletion__completed_at", filter=published),
    )

    return employees

def get_employee(user_id):
    """Получает сотрудника из базы данных или возвращает HTTP 404, если подходящий сотрудник не найден"""
    return get_object_or_404(_employees_queryset(), pk=user_id)

def add_completion_date_each_module(*, modules, completions):
    """Связывает каждый опубликованный модуль с датой его завершения конкретным сотрудником"""
    for module in modules:
        module.employee_completed_at = completions.get(module.id)

def _employees_queryset():
    """Возвращает исходный QuerySet сотрудников"""
    return get_user_model().objects.filter(
        is_active=True, is_superuser=False, is_staff=False,
    ).exclude(groups__name="HR")
