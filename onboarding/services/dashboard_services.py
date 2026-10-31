def calculate_general_statistics(*, employees, total_modules):
    """Рассчитывает общее количество сотрудников и распределяет их по состоянию обучения"""
    employees_count = employees.count()

    finished_count = employees.filter(
        completed_count=total_modules
    ).count() if total_modules else 0

    in_progress_count = employees.filter(
        completed_count__gt=0,
        completed_count__lt=total_modules,
    ).count()

    return {
        'employees_count': employees_count,
        'finished_count': finished_count,
        'in_progress_count': in_progress_count,
        'not_started_count' : employees_count - in_progress_count - finished_count
    }

def calculate_progress_percentage(*, page, total_modules):
    """Рассчитывает процент прохождения обучения для каждого сотрудника на текущей странице"""
    for employee in page.object_list:
        employee.progress_percent = calculate_progress_percent(completed_count=employee.completed_count, total_modules=total_modules)

def calculate_progress_percent(*, completed_count, total_modules):
    """Возвращает процент прохождения обучения"""
    return round(completed_count / total_modules * 100) if total_modules else 0

def calculate_answers_statistics(*, modules, counts) -> list[dict]:
    """Строит сводку ответов: по каждому вопросу — количество, проценты и доля верных."""
    blocks = []
    for module in modules:
        questions = []
        for question in module.questions.all():
            options = list(question.options.all())
            total = sum(counts.get(option, 0) for option in options)
            scored = question.is_scored

            rows = []
            for option in options:
                count = counts.get(option.id, 0)
                rows.append({
                    "text": option.text,
                    "count": count,
                    "percent": calculate_progress_percent(completed_count=count, total_modules=total),
                    "is_correct": option.is_correct if scored else None,
                })

            correct_count = sum(row["count"] for row in rows if row["is_correct"])
            questions.append({
                "text": question.text,
                "scored": scored,
                "total": total,
                "rows": rows,
                "correct_percent": (
                    calculate_progress_percent(completed_count=correct_count, total_modules=total)
                    if scored and total
                    else None
                ),
            })
        blocks.append({"module": module, "questions": questions})
    return blocks