from django.core.management.base import BaseCommand, CommandError

from ...services.catalog_sync import sync_questionnaires

class Command(BaseCommand):
    help = "Синхронизирует определения анкет с базой данных"

    def handle(self, *args, **options):
        try:
            result = sync_questionnaires()
        except ValueError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(f"Создано анкет: {result['questionnaires_created']}")

        
        