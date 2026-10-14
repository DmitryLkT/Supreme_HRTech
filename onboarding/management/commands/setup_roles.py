from django.contrib.auth.models import Permission, Group
from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from onboarding.models import ModuleCompletion

#Создает группу HR и назначает право просмотра прогресса.
class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **options):
        content_type = ContentType.objects.get_for_model(ModuleCompletion)

        try:
            permission = Permission.objects.get(
                content_type=content_type,
                codename="view_employee_progress"
            )
        except Permission.DoesNotExist:
            raise CommandError("Право просмотра прогресса еще не создано.")

        group, create = Group.objects.get_or_create(name="HR")
        group.permissions.set([permission])

        if create:
            message="Группа HR создана."
        else:
            message="Группа HR уже существует, права обновлены."

        self.stdout.write(self.style.SUCCESS(message))
        self.stdout.write("Назначено право: onboarding.view_employee_progress")
