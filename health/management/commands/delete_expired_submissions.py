from django.core.management.base import BaseCommand
from django.utils import timezone

from health.models import Submission, Answer


class Command(BaseCommand):
    def handle(self, *args, **options):
        today = timezone.localdate()

        expired_submissions = Submission.objects.filter(expires_at__lte=today)

        deleted_total, deleted_by_model = expired_submissions.delete()

        submission_count = deleted_by_model.get(Submission._meta.label, 0)
        answer_count = deleted_by_model.get(Answer._meta.label, 0)

        self.stdout.write(
            self.style.SUCCESS(
                f"Удалено прохождений: {submission_count}, ответов: {answer_count}."
            )
        )
