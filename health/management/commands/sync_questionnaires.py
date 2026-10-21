from django.core.management.base import BaseCommand, CommandError

from ...services.catalog_sync import sync_questionnaires

class Command(BaseCommand):
    help = "Синхронизирует определения анкет с базой данных"

    def handle(self, *args, **options):
        try:
            result = sync_questionnaires()
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(f"Создано анкет: {result['questionnaires_created']}\n"
                          f"Обновленно анкет: {result['questionnaires_updated']}\n"
                          f"Создано версий: {result['versions_created']}")
        