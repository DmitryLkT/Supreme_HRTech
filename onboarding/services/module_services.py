from django.shortcuts import get_object_or_404

from ..models import Module, ModuleCompletion

def get_module_detail(*, user, module_id):
    """Возвращает информацию - статус прохождения"""
    module = get_object_or_404(
        Module.objects.prefetch_related("questions__options"),
        id=module_id, is_published=True,
    )

    is_completed = ModuleCompletion.objects.filter(user=user, module=module).exists()

    return {
        "module": module,
        "is_completed": is_completed
    }

def get_module(*, user, module_id):
    """Получает модуль и создаёт запись о прохождении"""
    module = get_object_or_404(Module, id=module_id, is_published=True)
    ModuleCompletion.objects.get_or_create(user=user, module=module)

    return module

def get_published_modules():
    """Получает все опубликованные учебные модули и преобразует в обычный список."""
    return list(Module.objects.filter(is_published=True))

def get_number_published_modules():
    """Определяет, сколько модулей обучения опубликовано и учитывается при расчёте прогресса"""
    return Module.objects.filter(is_published=True).count()

def get_completion_dates_modules_employee(employee):
    """Получает записи о завершении опубликованных модулей конкретным сотрудником"""
    return {
        item.module_id: item.completed_at
        for item in ModuleCompletion.objects.filter(user=employee, module__is_published=True)
    }