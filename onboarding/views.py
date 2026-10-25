from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from django.db import transaction
from django.db.models import F

from .models import AnswerOption, AnswerSubmission, Module, ModuleCompletion, Question
from .permissions import employee_required, is_hr


@login_required
def home(request):
    if request.user.is_superuser:
        return redirect("admin:index")
    if is_hr(request.user):
        return redirect("hr_dashboard")
    if request.user.groups.filter(name="HR").exists():
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Группе HR не назначено право просмотра прогресса.")

    modules = list(Module.objects.filter(is_published=True).order_by("order", "id"))
    completed_module_ids = set(
        ModuleCompletion.objects.filter(
            user=request.user, module__is_published=True,
        ).values_list("module_id", flat=True)
    )
    total_modules = len(modules)
    completed_count = len(completed_module_ids)
    progress_percent = round(completed_count / total_modules * 100) if total_modules else 0
    next_module = next(
        (module for module in modules if module.id not in completed_module_ids),
        None,
    )
    return render(request, "onboarding/home.html", {
        "page_title": "Твой маршрут адаптации",
        "modules": modules,
        "completed_module_ids": completed_module_ids,
        "total_modules": total_modules,
        "completed_count": completed_count,
        "progress_percent": progress_percent,
        "next_module": next_module,
    })


@employee_required
def module_detail(request, module_id):
    module = get_object_or_404(
        Module.objects.prefetch_related("questions__options"),
        id=module_id, is_published=True,
    )
    is_completed = ModuleCompletion.objects.filter(user=request.user, module=module).exists()
    return render(request, "onboarding/module_detail.html", {
        "module": module, "is_completed": is_completed,
    })


@employee_required
@require_POST
def complete_module(request, module_id):
    module = get_object_or_404(Module, id=module_id, is_published=True)
    ModuleCompletion.objects.get_or_create(user=request.user, module=module)
    return redirect("module_detail", module_id=module.id)


@employee_required
@require_POST
def answer_question(request, question_id):
    question = get_object_or_404(Question, id=question_id, module__is_published=True)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    option_id = request.POST.get("option_id")

    if not option_id or not option_id.isdecimal():
        message = "Выбери вариант ответа."
        if is_ajax:
            return JsonResponse({"error": message, "message": message}, status=400)
        return render(request, "onboarding/question_result.html", {
            "question": question, "error": message,
        }, status=400)

    selected_option = get_object_or_404(AnswerOption, id=option_id, question=question)
    scored = question.is_scored
    correct_option = question.options.filter(is_correct=True).first() if scored else None
    is_correct = selected_option.is_correct if scored else None

    with transaction.atomic():
        submission, created = AnswerSubmission.objects.get_or_create(
            user=request.user, question=question,
            defaults={"option": selected_option, "is_correct": is_correct},
        )
        if not created:
            AnswerSubmission.objects.filter(pk=submission.pk).update(
                option=selected_option, is_correct=is_correct,
                attempts=F("attempts") + 1,
            )

    if not scored:
        message = "Ответ записан. Здесь нет правильного и неправильного: важно, как ты поступил бы на самом деле."
    elif is_correct:
        message = "Правильно!"
    else:
        message = "Неверно. Попробуй ещё раз."
        if correct_option:
            message += f" Правильный ответ: {correct_option.text}"

    if is_ajax:
        return JsonResponse({"is_correct": is_correct, "scored": scored, "message": message})
    return render(request, "onboarding/question_result.html", {
        "question": question,
        "selected_option": selected_option,
        "scored": scored,
        "is_correct": is_correct,
        "correct_option": correct_option,
        "message": message,
    })
