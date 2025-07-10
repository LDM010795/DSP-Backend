from django.core.management.base import BaseCommand
from core.employees.models import Tool, Employee, EmployeeToolAccess

TOOLS = [
    {
        "slug": "shift-planner",
        "name": "Shift Planner",
        "frontend_url": "http://localhost:5174",
    },
    {
        "slug": "elearning",
        "name": "E-Learning",
        "frontend_url": "http://localhost:5173",
    },
]

class Command(BaseCommand):
    help = "Erzeugt Standard-Tools und vergibt optional allen aktiven Employees Zugriff auf E-Learning."

    def add_arguments(self, parser):
        parser.add_argument(
            "--grant-elearning-all",
            action="store_true",
            help="Vergibt allen aktiven Mitarbeitern Zugriff auf E-Learning.",
        )

    def handle(self, *args, **options):
        for tool_data in TOOLS:
            tool, created = Tool.objects.get_or_create(slug=tool_data["slug"], defaults=tool_data)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Tool {tool.slug} angelegt."))
        if options["grant_elearning_all"]:
            elearning = Tool.objects.get(slug="elearning")
            employees = Employee.objects.filter(is_active=True)
            count = 0
            for emp in employees:
                _, created = EmployeeToolAccess.objects.get_or_create(employee=emp, tool=elearning)
                if created:
                    count += 1
            self.stdout.write(self.style.SUCCESS(f"{count} Freigaben für E-Learning erstellt.")) 