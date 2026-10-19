from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from health.models import AnswerOption, Questionnaire, QuestionQuestionnaire

C = QuestionQuestionnaire.Category

TITLE = "Самочувствие на работе"
VERSION = 1

FREQUENCY = ["Никогда", "Редко", "Иногда", "Часто", "Почти постоянно"]
DIFFICULTY = ["Совсем не трудно", "Немного трудно", "Умеренно трудно", "Очень трудно", "Крайне трудно"]
DROP = ["Совсем не снизилось", "Незначительно", "Умеренно", "Сильно", "Очень сильно"]

QUESTIONS = [
    (C.MOOD, "Как часто ты чувствовал себя подавленно или испытывал негативные эмоции именно из-за работы?", FREQUENCY),
    (C.MOOD, "Насколько часто к концу рабочего дня ты чувствовал эмоциональное истощение?", FREQUENCY),
    (C.WORKLOAD, "Насколько часто объём работы был чрезмерным для доступного времени?", FREQUENCY),
    (C.WORKLOAD, "Насколько часто ты испытывал стресс из-за рабочих задач, сроков или ответственности?", FREQUENCY),
    (C.ORGANIZATION, "Насколько часто тебе было непонятно, что именно нужно делать или какой результат от тебя ожидают?", FREQUENCY),
    (C.ORGANIZATION, "Насколько часто нехватка людей, информации, инструментов или согласований мешала нормально работать?", FREQUENCY),
    (C.TEAM, "Насколько часто ты сталкивался с напряжением, конфликтами или неуважительным отношением на работе?", FREQUENCY),
    (C.TEAM, "Насколько трудно тебе было получить помощь или открыто сообщить о проблеме коллегам либо руководителю?", DIFFICULTY),
    (C.MOTIVATION, "Насколько сильно за последнюю неделю снизилось твоё желание включаться в работу по сравнению с обычным уровнем?", DROP),
]

COMMENT_PROMPT = "Что сильнее всего повлияло на твою рабочую неделю?"


class Command(BaseCommand):
    help = "Создаёт и публикует анкету «Самочувствие на работе» (9 вопросов, 5 вариантов, оценки 1–5)."

    @transaction.atomic
    def handle(self, *args, **options):
        if Questionnaire.objects.filter(title=TITLE, version=VERSION).exists():
            self.stdout.write("Анкета уже существует, ничего не изменено.")
            return

        questionnaire = Questionnaire.objects.create(
            title=TITLE,
            description="Короткий еженедельный опрос: настроение, нагрузка, организация работы, команда, мотивация.",
            comment_prompt=COMMENT_PROMPT,
            version=VERSION,
        )
        for order, (category, text, labels) in enumerate(QUESTIONS, start=1):
            question = QuestionQuestionnaire.objects.create(
                questionnaire=questionnaire, category=category, text=text, order=order,
            )
            AnswerOption.objects.bulk_create([
                AnswerOption(question=question, text=label, order=score, score=score)
                for score, label in enumerate(labels, start=1)
            ])

        try:
            questionnaire.publish()
        except ValidationError as error:
            self.stdout.write(self.style.WARNING(
                f"Анкета создана как черновик, не опубликована: {' '.join(error.messages)}"
            ))
            return
        self.stdout.write(self.style.SUCCESS("Анкета создана и опубликована."))
