"""Подсчёт показателей анкеты самочувствия.

Показатель = среднее арифметическое оценок (1–5) по вопросам одной категории.
Чем выше оценка, тем сильнее выражена проблема.
"""
from .models import QuestionQuestionnaire

# (верхняя граница — не включая, код уровня, подпись)
LEVELS = [
    (2, "low", "Низкая выраженность проблем"),
    (3, "moderate", "Умеренные сигналы"),
    (4, "notable", "Заметная проблема, нужна проверка"),
    (None, "strong", "Сильный сигнал, нужна приоритетная проверка"),
]


def interpret(average):
    """1,0–1,9 низкая; 2,0–2,9 умеренные; 3,0–3,9 заметная; 4,0–5,0 сильный сигнал."""
    for upper, code, label in LEVELS:
        if upper is None or average < upper:
            return code, label


def format_number(value):
    return f"{value:.1f}".replace(".", ",")


def category_scores(pairs):
    """pairs — итерируемое из (категория, оценка).

    Возвращает список по всем категориям, в которых есть ответы,
    в порядке, заданном QuestionQuestionnaire.Category.
    """
    sums, counts = {}, {}
    for category, score in pairs:
        sums[category] = sums.get(category, 0) + score
        counts[category] = counts.get(category, 0) + 1

    result = []
    for key, label in QuestionQuestionnaire.Category.choices:
        if key not in counts:
            continue
        average = sums[key] / counts[key]
        level, level_label = interpret(average)
        result.append({
            "key": key,
            "label": label,
            "average": average,
            "display": format_number(average),
            "level": level,
            "level_label": level_label,
            "count": counts[key],
        })
    return result


def completion_pairs(completion):
    """Пары (категория, оценка) из ответов одного прохождения анкеты."""
    return [
        (answer.question_questionnaire.category, answer.answer_option.score)
        for answer in completion.answeruser_set.all()
    ]
