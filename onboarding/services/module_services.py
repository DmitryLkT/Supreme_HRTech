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