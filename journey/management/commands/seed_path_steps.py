from django.core.management.base import BaseCommand

from journey.models import PathStep

# ПРИМЕР структуры. Содержание шагов должны утвердить компания и руководитель.
EXAMPLE_STEPS = [
    (30, "Получить доступы и инструменты"),
    (30, "Пройти модули адаптации"),
    (30, "Первая задача вместе с наставником"),
    (30, "Встреча 1:1 с руководителем"),
    (60, "Самостоятельно вести небольшую задачу"),
    (60, "Познакомиться со смежными командами"),
    (60, "Поговорить с руководителем о нагрузке"),
    (90, "Взять ответственность за результат своей зоны"),
    (90, "Итоговая встреча по испытательному сроку"),
    (90, "Дать отзыв об онбординге"),
]


class Command(BaseCommand):
    help = "Создаёт ПРИМЕРНЫЕ шаги пути 30/60/90 (с пометкой «пример»). Повторный запуск ничего не дублирует."

    def handle(self, *args, **options):
        if PathStep.objects.exists():
            self.stdout.write("Шаги уже есть, ничего не добавлено.")
            return
        PathStep.objects.bulk_create([
            PathStep(period=period, title=title, order=index, is_placeholder=True)
            for index, (period, title) in enumerate(EXAMPLE_STEPS, start=1)
        ])
        self.stdout.write(self.style.SUCCESS(f"Добавлено шагов: {len(EXAMPLE_STEPS)} (отмечены как пример)."))