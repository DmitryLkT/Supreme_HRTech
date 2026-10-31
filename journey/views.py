from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from onboarding.hr_views import employees_queryset
from onboarding.permissions import employee_required, hr_required

from journey.services.models_services import get_list_path_step, get_done_ids, get_periods_from_path_steps, get_published_path_step, toggle_path_step_progress, get_mentor_question, save_mentor_answer
from journey.services.dashboard_services import get_steps_with_done_count, calculate_steps_progress
from journey.services.mentor_services import get_mentor_questions, get_mentor_question_data, validate_mentor_question, create_mentor_question, get_mentor_questions_show, get_mentor_questions_for_hr, get_open_mentor_questions_count

from .models import MentorQuestion

QUESTION_MAX_LENGTH = 1000
ANSWER_MAX_LENGTH = 2000
PERIOD_DESCRIPTIONS = {
    30: "Освоиться: понять роль, людей и процессы.",
    60: "Работать самостоятельно в знакомых задачах.",
    90: "Отвечать за результат и подвести итоги испытательного срока.",
}


def day_of_path(user):
    """Номер дня с даты создания аккаунта; от 1 до 90."""
    joined = timezone.localtime(user.date_joined).date()
    days = (timezone.localdate() - joined).days + 1
    return max(1, min(days, 90))

def get_answer_text(*, request):
    """Извлекает и нормализует текст ответа из POST"""
    return request.POST.get("answer", "").strip()[:ANSWER_MAX_LENGTH]

def current_period(day):
    return 30 if day <= 30 else 60 if day <= 60 else 90


@employee_required
@require_GET
def path(request):
    """Формирует страницу пути онбординга сотрудника с прогрессом по периодам."""
    if request.user.is_superuser:
        return redirect("hr_path")

    steps = get_list_path_step()
    done_ids = get_done_ids(request=request, steps=steps)

    day = day_of_path(request.user)
    now_period = current_period(day)

    periods = get_periods_from_path_steps(PERIOD_DESCRIPTIONS=PERIOD_DESCRIPTIONS,
                                         steps=steps,
                                         done_ids=done_ids,
                                         now_period=now_period)

    day_percent = round(day / 90 * 100)

    return render(request, "journey/path.html", {
        "periods": periods,
        "day": day,
        "day_percent": day_percent,
        "has_steps": bool(steps),
        "has_placeholder": any(s.is_placeholder for s in steps),
        "done_total": len(done_ids), "steps_total": len(steps),
    })


@employee_required
@require_POST
def toggle_step(request, step_id):
    """Переключает отметку о выполнении шага пути сотрудника"""
    if request.user.is_superuser:
        return redirect("hr_path")

    step = get_published_path_step(step_id)
    toggle_path_step_progress(user=request.user, step=step)

    return redirect("path")


@hr_required
@require_GET
def hr_path(request):
    """Формирует HR-страницу прогресса сотрудников по шагам пути онбординга"""
    employees = employees_queryset()

    steps = get_steps_with_done_count(employees=employees)
    employees_total = employees.count()

    rows = calculate_steps_progress(steps=steps, employees_total=employees_total)

    return render(request, "journey/hr_path.html", {
        "rows": rows, "employees_total": employees_total,
    })


@employee_required
@require_http_methods(["GET", "POST"])
def mentor(request):
    """Формирует страницу вопросов наставнику и обрабатывает отправку нового вопроса"""
    if request.user.is_superuser:
        return redirect("hr_mentor")

    error = ""
    text = ""
    category = MentorQuestion.Category.TASK

    if request.method == "POST":
        text, category = get_mentor_question_data(request=request)
        error = validate_mentor_question(text=text, QUESTION_MAX_LENGTH=QUESTION_MAX_LENGTH)
        if not error:
            create_mentor_question(user=request.user, text=text, category=category)
            return redirect("mentor")

    questions = get_mentor_questions(user=request.user)

    return render(request, "journey/mentor.html", {
        "questions": questions,
        "categories": MentorQuestion.Category.choices,
        "error": error, "text": text, "category": category,
        "max_length": QUESTION_MAX_LENGTH,
    }, status=400 if error else 200)


@hr_required
@require_GET
def hr_mentor(request):
    """Формирует HR-страницу вопросов наставнику с фильтром по ответам"""
    show = get_mentor_questions_show(request=request)

    questions = get_mentor_questions_for_hr(show=show)
    open_count = get_open_mentor_questions_count()

    return render(request, "journey/hr_mentor.html", {
        "questions": questions[:100],
        "show": show,
        "open_count": open_count,
        "max_length": ANSWER_MAX_LENGTH,
    })


@hr_required
@require_POST
def hr_mentor_answer(request, question_id):
    """Сохраняет ответ HR на вопрос наставнику"""
    question = get_mentor_question(question_id)

    answer = get_answer_text(request=request)

    save_mentor_answer(question=question, answer=answer, user=request.user)

    return redirect("hr_mentor")