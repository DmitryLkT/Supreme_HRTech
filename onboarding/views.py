from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied

from onboarding.services.permissions_service import employee_required, is_hr
from onboarding.services.module_services import get_module_detail, get_module
from onboarding.services.progress_services import get_user_module_progress
from onboarding.services.question_service import get_question, get_answer_option_question, validate_answer_option_id, check_answer

@login_required
def home(request):
    """Рендерит главную страницу с данными о прогрессе"""
    redirect_response = get_home_access_redirect(request.user)
    if redirect_response:
        return redirect_response

    context = get_user_module_progress(request.user)

    return render(request, "onboarding/home.html", context)

@employee_required
def module_detail(request, module_id):
    """Рендерит страницу с информацией прошел ли текущий пользователь конкреный модуль"""
    context = get_module_detail(user=request.user, module_id=module_id)

    return render(request, "onboarding/module_detail.html", context)

@employee_required
@require_POST
def complete_module(request, module_id):
    """Помечает текущий модуль как пройденный текущим сотрудником"""
    module = get_module(user=request.user, module_id=module_id)
    return redirect("module_detail", module_id=module.pk)

@employee_required
@require_POST
def answer_question(request, question_id):
    """Обрабатывает ответ сотрудника на вопрос"""
    question = get_question(question_id)
    option_id = request.POST.get("option_id")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    error = validate_answer_option_id(option_id)

    if error:
        if is_ajax:
            return JsonResponse({"error": error, "is_ajax": is_ajax})
        return render(request, "onboarding/question_result.html",
                      {
                          "question": question,
                          "error": error
                      }, status=400)

    selected_option = get_answer_option_question(question=question, option_id=option_id)

    context = check_answer(question=question, selected_option=selected_option)
    if is_ajax:
        return JsonResponse({
            "is_correct": context["is_correct"],
            "message": context["message"]
        })

    return render(request, "onboarding/question_result.html", context)

def get_home_access_redirect(user):
    """Возвращает redirect или None"""
    if user.is_superuser:
        return redirect("admin:index")
    if is_hr(user):
        return redirect("hr_dashboard")
    if user.groups.filter(name="HR").exists():
        raise PermissionDenied("Группе HR не назначено право просмотра прогресса.")

    return None