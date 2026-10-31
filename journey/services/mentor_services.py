from ..models import MentorQuestion

def get_mentor_questions(*, user):
    """Возвращает вопросы сотрудника наставнику"""
    return MentorQuestion.objects.filter(user=user)


def get_mentor_question_data(*, request):
    """Извлекает и нормализует текст и категорию вопроса из POST"""
    text = request.POST.get("text", "").strip()
    raw_category = request.POST.get("category", "")
    category = (raw_category
                if raw_category in MentorQuestion.Category.values
                else MentorQuestion.Category.OTHER)
    return text, category


def validate_mentor_question(*, text, QUESTION_MAX_LENGTH):
    """Проверяет текст вопроса"""
    if not text:
        return "Напиши вопрос."
    if len(text) > QUESTION_MAX_LENGTH:
        return f"Вопрос длиннее {QUESTION_MAX_LENGTH} символов. Сократи его."
    return None


def create_mentor_question(*, user, text, category):
    """Сохраняет вопрос наставнику"""
    MentorQuestion.objects.create(user=user, category=category, text=text)

def get_mentor_questions_show(*, request):
    """Возвращает выбранный фильтр вопросов: "open" (без ответа) или "all" """
    show = request.GET.get("show", "open")
    return "all" if show == "all" else "open"


def get_mentor_questions_for_hr(*, show):
    """Возвращает вопросы наставнику для HR: без ответа или все, с авторами"""
    questions = MentorQuestion.objects.select_related("user").order_by("-created_at")
    if show != "all":
        questions = questions.filter(answer="")
    return questions


def get_open_mentor_questions_count():
    """Возвращает количество вопросов наставнику без ответа"""
    return MentorQuestion.objects.filter(answer="").count()
