import logging
import random # Import random for selecting modules
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import timedelta # timedelta hinzufügen
from django.utils import timezone # timezone hinzufügen
from decimal import Decimal, ROUND_HALF_UP # Import Decimal
# Corrected import path assuming models.py is in the parent 'modules' directory
from ...models import Module, Content, Task, SupplementaryContent, UserTaskProgress
from django.contrib.auth.models import User # Import User model
# Import von Exam-Modellen
try:
    from ...models import Exam, ExamCriterion, ExamRequirement, ExamAttempt, CriterionScore, ExamDifficulty, CertificationPath # ExamDifficulty hinzugefügt
    EXAMS_AVAILABLE = True
except ImportError:
    EXAMS_AVAILABLE = False
    CertificationPath = None # Sicherstellen, dass CertificationPath None ist bei Fehler
    logging.warning("Die App 'final_exam' wurde nicht gefunden oder Modelle fehlen. Prüfungen und Zertifikatspfade werden nicht erstellt/verarbeitet.")

# Configure logger
logger = logging.getLogger(__name__)

# Helper list for plausible module titles - WIRD JETZT DURCH DICT ERSETZT
# PLAUSIBLE_MODULE_TITLES = [...] # Alte Liste

# NEU: Zuordnung von Titeln zu Kategorien - Zugriff über Module.
MODULE_CATEGORIES_MAP = {
    # Python
    "Python Grundlagen": "Python",
    "Python Datenstrukturen": "Python",
    "Python Kontrollfluss": "Python",
    "Python Funktionen Deep Dive": "Python",
    "OOP in Python": "Python",
    "Python Module und Pakete": "Python",
    "Fehlerbehandlung in Python": "Python",
    "Dateiverarbeitung in Python": "Python",
    "Python Standardbibliothek Highlights": "Python",
    "List Comprehensions & Generators": "Python",
    "Testing in Python (unittest, pytest)": "DevOps & Tools",

    # Web Development
    "HTML Grundlagen": "Web Development",
    "CSS Grundlagen": "Web Development",
    "CSS Flexbox & Grid": "Web Development",
    "JavaScript Basics": "Web Development",
    "DOM Manipulation": "Web Development",
    "Asynchrones JavaScript (Promises, async/await)": "Web Development",
    "React Grundlagen": "Web Development",
    "React State Management (useState, useContext)": "Web Development",
    "React Routing (React Router)": "Web Development",
    "React Fortgeschrittene Hooks": "Web Development",
    "Next.js Einführung": "Web Development",
    "Next.js App Router": "Web Development",
    "Django Grundlagen": "Web Development",
    "Django Models & ORM": "Web Development",
    "Django Views & Templates": "Web Development",
    "Django Forms": "Web Development",
    "Django REST Framework Basics": "Web Development",
    "API Design Principles": "Web Development",
    "Flask Einführung": "Sonstiges",

    # Data Science & Analysis
    "Datenanalyse mit NumPy": "Data Science",
    "Datenanalyse mit Pandas": "Data Science",
    "Datenvisualisierung mit Matplotlib": "Data Science",
    "Datenvisualisierung mit Seaborn": "Data Science",
    "Einführung in Machine Learning": "Data Science",
    "Scikit-learn Grundlagen": "Data Science",

    # DevOps & Tools
    "Git Grundlagen": "DevOps & Tools",
    "Docker Einführung": "DevOps & Tools",
    "Linux Kommandozeile Basics": "DevOps & Tools",
    "Datenbanken Grundlagen (SQL)": "DevOps & Tools",
}

# Helper list for plausible exam titles
PLAUSIBLE_EXAM_TITLES = [
    "Webshop Backend Implementierung (Django)", "Interaktives Dashboard (React)", "Datenanalyse-Pipeline (Pandas)",
    "REST API Entwicklung (DRF)", "Algorithmen-Challenge", "Full-Stack Blog-Anwendung (Next.js/Django)",
    "Machine Learning Modell Training", "Automatisierte Testsuite", "Cloud Deployment Aufgabe",
    "System Design Interview Simulation", "CSS Layout-Masterclass", "JavaScript DOM-Projekt",
    "Datenbank-Modellierungsaufgabe", "Sicherheitsüberprüfung einer Webanwendung", "Python Code-Refactoring Aufgabe",
    "API-Integration Projekt", "Asynchrone Datenverarbeitung", "Flask Microservice", "NumPy Performance-Optimierung",
    "React Native App Prototyp"
]

# Helper list for plausible requirements
PLAUSIBLE_REQUIREMENTS = [
    "Implementiere die angegebene Funktionalität vollständig.",
    "Schreibe sauberen, lesbaren und gut dokumentierten Code.",
    "Halte dich an gängige Best Practices und Coding Conventions (z.B. PEP 8 für Python).",
    "Erstelle Unit-Tests für kritische Komponenten mit ausreichender Code Coverage.",
    "Nutze das vorgegebene Framework/die Bibliothek effektiv.",
    "Achte auf eine sinnvolle Projektstruktur.",
    "Behandle mögliche Fehlerfälle robust.",
    "Optimiere den Code hinsichtlich Performance (falls relevant).",
    "Erstelle eine verständliche README-Datei zur Einrichtung und Ausführung.",
    "Versioniere deinen Code mit Git und erstelle aussagekräftige Commit-Messages."
]

# Helper list for plausible criteria
PLAUSIBLE_CRITERIA = [
    ("Funktionalität", "Korrekte Umsetzung aller Anforderungen", 30),
    ("Code-Qualität", "Lesbarkeit, Struktur, Kommentare, PEP 8", 20),
    ("Testing", "Qualität und Abdeckung der Unit-Tests", 15),
    ("Konzept/Architektur", "Sinnvoller Aufbau, Nutzung von Design Patterns", 15),
    ("Dokumentation", "README, API-Dokumentation, Kommentare", 10),
    ("Effizienz/Performance", "Laufzeitverhalten, Speicherverbrauch (falls relevant)", 10)
]

class Command(BaseCommand):
    help = 'Cleans and seeds the database with extensive test data for Python modules and exams.' # Updated help text

    # Passe _create_module an, um Kategorie zu akzeptieren
    def _create_module(self, title, category, is_public=True):
        module, created = Module.objects.get_or_create(
            title=title,
            defaults={
                'is_public': is_public,
                'category': category # Füge Kategorie zu Defaults hinzu
            }
        )
        tasks = []
        if created:
            # self.stdout.write(self.style.SUCCESS(f'Created Module: "{title}"')) # Weniger Output
            # Immer 1-3 simple Tasks für neue Module hinzufügen
            num_tasks = random.randint(1, 3)
            for i in range(num_tasks):
                task_title = f"Aufgabe {i+1}: Print-Ausgabe ({title[:20]}...)"
                task_desc = f"Schreibe eine Python-Funktion `task_{i+1}()`, die den String 'Modul: {title}, Aufgabe {i+1}' ausgibt."
                test_path = f"task_tests/common/test_print_task.py" # Generischer Pfad
                difficulty = random.choice(Task.Difficulty.choices)[0]
                hint = "Benutze die print()-Funktion."
                task = self._create_task(module, task_title, task_desc, difficulty, test_path, i+1, hint)
                tasks.append(task)
        # Wenn Modul schon existierte, hole seine Tasks
        if not tasks:
            tasks = list(module.tasks.all())
        return module, tasks

    def _create_content(self, module, title, description, order, video_url=None, supplementary_title=None):
        content, created = Content.objects.get_or_create(
            module=module,
            title=title,
            defaults={
                'description': description,
                'order': order,
                'video_url': video_url or f'https://www.youtube.com/watch?v=example_{random.randint(1000, 9999)}', # Placeholder video
                'supplementary_title': supplementary_title
            }
        )
        # if created:
        #     self.stdout.write(self.style.SUCCESS(f'  - Created Content: "{title}"'))
        # else:
        #     self.stdout.write(f'  - Content "{title}" already exists.')
        return content

    def _create_task(self, module, title, description, difficulty, test_path, order, hint=None):
        task, created = Task.objects.get_or_create(
            module=module,
            title=title,
            defaults={
                'description': description,
                'difficulty': difficulty,
                'test_file_path': test_path,
                'order': order,
                'hint': hint or f"Standard-Hinweis für {title}"
            }
        )
        # if created:
        #     self.stdout.write(self.style.SUCCESS(f'  - Created Task: "{title}" (Tests: {test_path})'))
        # else:
        #     self.stdout.write(f'  - Task "{title}" already exists.')
        return task

    # --- Methods for Exam Generation ---
    def _create_exam(self, title, duration_weeks, difficulty, description, modules=None, requirements=None):
        """
        Erstellt eine Prüfung mit optionalen Modulvoraussetzungen und Anforderungen.
        """
        if not EXAMS_AVAILABLE:
            self.stdout.write(self.style.WARNING(f'Überspringe Prüfung "{title}": App final_exam nicht verfügbar.'))
            return None

        exam, created = Exam.objects.get_or_create(
            title=title,
            defaults={
                'duration_weeks': duration_weeks,
                'difficulty': difficulty,
                'description': description,
            }
        )
        exam_criteria = []

        if created:
            self.stdout.write(self.style.SUCCESS(f'Prüfung erstellt: "{title}"'))
        # else:
            # self.stdout.write(f'Prüfung "{title}" existiert bereits.')

        # Module zuweisen (clear existing first)
        exam.modules.clear()
        if modules:
            exam.modules.set(modules)
            # self.stdout.write(f'  - Module zugewiesen: {[m.title for m in modules]}')

        # Anforderungen erstellen/aktualisieren (clear existing first)
        exam.requirements.all().delete()
        if requirements:
            for index, req_desc in enumerate(requirements):
                ExamRequirement.objects.create(
                    exam=exam,
                    description=req_desc,
                    order=index + 1 # Reihenfolge 1-basiert
                )
            # self.stdout.write(f'  - {len(requirements)} Anforderungen erstellt.')

        # Kriterien erstellen/aktualisieren (clear existing first)
        exam.criteria.all().delete()
        for crit_title, crit_desc, crit_points in PLAUSIBLE_CRITERIA:
             criterion = self._create_exam_criterion(exam, crit_title, crit_desc, crit_points)
             if criterion:
                 exam_criteria.append(criterion)

        return exam, exam_criteria # Return exam and its criteria

    def _create_exam_criterion(self, exam, title, description, max_points):
        """
        Erstellt ein Bewertungskriterium für eine Prüfung.
        """
        if not EXAMS_AVAILABLE or not exam:
            return None

        criterion, created = ExamCriterion.objects.get_or_create(
            exam=exam,
            title=title,
            defaults={
                'description': description,
                'max_points': max_points,
            }
        )

        # if created:
        #     self.stdout.write(self.style.SUCCESS(f'  - Kriterium erstellt: "{title}" ({max_points} Pkt)'))
        # else:
        #     self.stdout.write(f'  - Kriterium "{title}" existiert bereits.')
        
        return criterion

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting database cleanup before seeding...'))

        # --- Cleanup existing data ---
        if EXAMS_AVAILABLE:
            self.stdout.write('Lösche Exam-bezogene Daten...')
            ExamRequirement.objects.all().delete()
            CriterionScore.objects.all().delete()
            ExamAttempt.objects.all().delete()
            ExamCriterion.objects.all().delete()
            # Clear M2M before deleting Exams
            for exam in Exam.objects.all():
                exam.modules.clear()
            Exam.objects.all().delete()
            self.stdout.write('  - Exam-Daten gelöscht.')

        SupplementaryContent.objects.all().delete()
        Content.objects.all().delete()
        UserTaskProgress.objects.all().delete()
        Task.objects.all().delete()
        Module.objects.all().delete() # This will cascade delete related Content, Task if configured
        self.stdout.write('  - Modul-Daten gelöscht.')

        User.objects.filter(username="test").delete()
        self.stdout.write('  - Test User gelöscht.')
        self.stdout.write(self.style.SUCCESS('Cleanup finished.'))

        # --- Create Test User ---
        self.stdout.write('Erstelle Test User...')
        test_user = User.objects.create_user(
            username="test",
            password="test",
            email="test@test.com",
            is_staff=True,
            is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS(f'Test User "{test_user.username}" erstellt.'))

        # --- Create Modules ---
        self.stdout.write(self.style.SUCCESS('Starting database seeding...'))
        all_modules = {} # Store module_obj: [task_obj1, ...]
        # Iteriere über das neue Dictionary
        for title, category in MODULE_CATEGORIES_MAP.items():
             # Übergebe die Kategorie an _create_module
             module_obj, task_objs = self._create_module(title, category)
             if module_obj:
                 all_modules[module_obj] = task_objs
                 # Add some basic content to each module
                 self._create_content(module_obj, f"Einführung in {title}", f"Grundlegende Konzepte von {title}.", 1)
                 if len(task_objs) > 0:
                    self._create_content(module_obj, f"Übungen zu {title}", f"Praktische Aufgaben zum Modul {title}.", 2)

        self.stdout.write(self.style.SUCCESS(f'{len(all_modules)} Module verarbeitet/erstellt.'))
        module_list = list(all_modules.keys()) # Get a list of module objects

        # --- Create Exams ---
        if EXAMS_AVAILABLE:
            self.stdout.write(f'Erstelle 20 Prüfungen...')
            all_exams = {} # Store exam_obj: [criterion_obj1, ...]
            created_exam_titles = set() # To avoid duplicate titles if PLAUSIBLE_EXAM_TITLES has duplicates

            # 1. Create 5 Exams without prerequisites
            self.stdout.write('  - Erstelle 5 Prüfungen ohne Voraussetzungen...')
            no_prereq_exam_titles = [
                "Offenes Coding-Projekt", "Logik-Rätsel in Python", "UI/UX Design Challenge",
                "Technisches Schreiben Aufgabe", "Datenbank-Abfrage Optimierung"
            ]
            for i in range(5):
                exam_title = no_prereq_exam_titles[i]
                exam_desc = f"Dies ist eine frei verfügbare Prüfung zum Thema {exam_title}. Keine Modulvoraussetzungen nötig."
                reqs = random.sample(PLAUSIBLE_REQUIREMENTS, k=random.randint(4, 6))
                exam_obj, criteria_objs = self._create_exam(
                    title=exam_title,
                    duration_weeks=random.randint(1, 2),
                    difficulty=random.choice([ExamDifficulty.EASY, ExamDifficulty.MEDIUM]),
                    description=exam_desc,
                    modules=None,
                    requirements=reqs
                )
                if exam_obj:
                    all_exams[exam_obj] = criteria_objs
                    created_exam_titles.add(exam_title)

            # 2. Create 15 Exams WITH prerequisites
            self.stdout.write('  - Erstelle 15 Prüfungen mit Voraussetzungen...')
            exam_titles_with_prereqs = [t for t in PLAUSIBLE_EXAM_TITLES if t not in created_exam_titles]
            if len(exam_titles_with_prereqs) < 15:
                 # Add generic titles if needed
                 exam_titles_with_prereqs.extend([f"Generische Prüfung Nr. {i+1}" for i in range(15 - len(exam_titles_with_prereqs))])

            for i in range(15):
                if not module_list: # Should not happen with 40 modules, but safety check
                     self.stdout.write(self.style.WARNING("Keine Module mehr verfügbar für Prüfungs-Voraussetzungen."))
                     break
                exam_title = exam_titles_with_prereqs[i]
                exam_desc = f"Prüfung zum Thema {exam_title}. Erfordert Abschluss spezifischer Module."
                reqs = random.sample(PLAUSIBLE_REQUIREMENTS, k=random.randint(5, 8))
                # Select 1 to 4 random modules as prerequisites
                num_modules = random.randint(1, min(4, len(module_list)))
                required_modules = random.sample(module_list, k=num_modules)
                exam_obj, criteria_objs = self._create_exam(
                    title=exam_title,
                    duration_weeks=random.randint(1, 4),
                    difficulty=random.choice(ExamDifficulty.choices)[0], # Get value like 'easy'
                    description=exam_desc,
                    modules=required_modules,
                    requirements=reqs
                )
                if exam_obj:
                    all_exams[exam_obj] = criteria_objs
                    created_exam_titles.add(exam_title)

            self.stdout.write(self.style.SUCCESS(f'{len(all_exams)} Prüfungen erstellt.'))
            exam_list = list(all_exams.keys()) # List of exam objects

            # --- Set User Task Progress ---
            self.stdout.write(f'Setze Aufgabenfortschritt für User "{test_user.username}"...')
            exams_to_make_available = []
            exams_with_prereqs = [e for e in exam_list if e.modules.exists()]

            if len(exams_with_prereqs) >= 5:
                # Select 5 exams that we want to make available for the user
                exams_to_make_available = random.sample(exams_with_prereqs, k=5)
                self.stdout.write(f'  - Ziel: Mache {len(exams_to_make_available)} Prüfungen verfügbar.')

                modules_to_complete = set()
                for exam in exams_to_make_available:
                    modules_to_complete.update(exam.modules.all())

                self.stdout.write(f'  - Dafür müssen {len(modules_to_complete)} Module abgeschlossen werden.')
                completed_tasks_count = 0
                for module in modules_to_complete:
                    if module in all_modules and all_modules[module]: # Check if module and its tasks exist
                        for task in all_modules[module]:
                            UserTaskProgress.objects.update_or_create(
                                user=test_user,
                                task=task,
                                defaults={'completed': True, 'completed_at': timezone.now()}
                            )
                            completed_tasks_count += 1
                self.stdout.write(self.style.SUCCESS(f'  - {completed_tasks_count} Aufgaben in erforderlichen Modulen als abgeschlossen markiert.'))

                # Ensure some other modules are NOT fully completed
                potential_incomplete_modules = [m for m in module_list if m not in modules_to_complete and m in all_modules and all_modules[m]]
                if potential_incomplete_modules:
                     module_to_make_incomplete = random.choice(potential_incomplete_modules)
                     tasks_in_incomplete_mod = all_modules[module_to_make_incomplete]
                     if len(tasks_in_incomplete_mod) > 1:
                         # Complete only the first task
                         UserTaskProgress.objects.update_or_create(
                             user=test_user,
                             task=tasks_in_incomplete_mod[0],
                             defaults={'completed': True, 'completed_at': timezone.now()}
                         )
                         # Delete progress for other tasks in this module
                         UserTaskProgress.objects.filter(user=test_user, task__in=tasks_in_incomplete_mod[1:]).delete()
                         self.stdout.write(f'  - Modul "{module_to_make_incomplete.title}" als teilweise abgeschlossen markiert (für Testzwecke).')

            else:
                 self.stdout.write(self.style.WARNING("Nicht genügend Prüfungen mit Voraussetzungen erstellt, um 5 verfügbar zu machen."))


            # --- Create specific Exam Attempts for Test User ---
            self.stdout.write('Erstelle spezifische Exam Attempts...')
            created_attempts_exams = set() # Track exams used for attempts

            # Helper function to mark prerequisites as completed
            def mark_prerequisites_complete(exam_obj, user_obj):
                completed_tasks_in_prereqs = 0
                required_modules = exam_obj.modules.all()
                if required_modules:
                    # self.stdout.write(f'    - Stelle sicher, dass Voraussetzungen für "{exam_obj.title}" erfüllt sind...')
                    for module in required_modules:
                        for task in module.tasks.all():
                            _, created = UserTaskProgress.objects.update_or_create(
                                user=user_obj,
                                task=task,
                                defaults={'completed': True, 'completed_at': timezone.now()}
                            )
                            if created:
                                completed_tasks_in_prereqs += 1
                    if completed_tasks_in_prereqs > 0:
                         self.stdout.write(f'    - {completed_tasks_in_prereqs} Aufgaben in Voraussetzungen für "{exam_obj.title}" als abgeschlossen markiert.')
                # else:
                    # self.stdout.write(f'    - Prüfung "{exam_obj.title}" hat keine Modul-Voraussetzungen.')


            # 1. Graded Attempt
            exam_for_graded = None
            possible_graded_exams = [e for e in exam_list if e not in exams_to_make_available]
            if not possible_graded_exams:
                possible_graded_exams = [e for e in exam_list if not e.modules.exists()] # Fallback to no-prereq
            
            if possible_graded_exams: # If Block 1
                 exam_for_graded = random.choice(possible_graded_exams)
                 criteria_for_graded = all_exams.get(exam_for_graded)

                 if criteria_for_graded: # If Block 2
                     try: # Try Block
                         # --- NEU: Voraussetzungen erfüllen ---
                         mark_prerequisites_complete(exam_for_graded, test_user)
                         # ------------------------------------

                         # Schritt 1: Attempt holen oder erstellen
                         graded_attempt, created = ExamAttempt.objects.get_or_create(
                             exam=exam_for_graded,
                             user=test_user,
                             # Hier keine Defaults für Status etc., die wir sowieso überschreiben
                             defaults={
                                 'started_at': timezone.now() - timedelta(days=30),
                                 'submitted_at': timezone.now() - timedelta(days=20),
                             }
                         )

                         # Schritt 2: Felder setzen (unabhängig von created)
                         graded_attempt.status = ExamAttempt.Status.GRADED
                         graded_attempt.feedback = "Sehr solide Leistung. Kleinere Verbesserungsmöglichkeiten im Bereich X."
                         graded_attempt.graded_at = timezone.now() - timedelta(days=10)
                         graded_attempt.graded_by = test_user

                         # Schritt 3: Attempt speichern, um sicher eine ID zu haben und Status zu aktualisieren!
                         graded_attempt.save()

                         # Schritt 4: CriterionScores erstellen (nachdem Attempt gespeichert wurde)
                         CriterionScore.objects.filter(attempt=graded_attempt).delete() # Alte Scores löschen
                         total_score = Decimal('0.00') # Use Decimal for total score as well
                         for criterion in criteria_for_graded:
                             # Calculate value first as float
                             raw_achieved = float(random.uniform(0.5, 1.0) * criterion.max_points)
                             # Convert to Decimal and quantize to exactly 2 decimal places
                             achieved = Decimal(str(raw_achieved)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
 
                             # Ensure achieved does not exceed max_points (due to rounding)
                             achieved = min(achieved, Decimal(str(criterion.max_points)))
                             
                             CriterionScore.objects.create(
                                 attempt=graded_attempt, # Jetzt hat graded_attempt sicher eine ID
                                 criterion=criterion,
                                 achieved_points=achieved
                             )
                             total_score += achieved

                         # Schritt 5: Finales Speichern mit dem Score (wird auch durch Signale ausgelöst, aber explizit ist sicher)
                         graded_attempt.score = total_score
                         graded_attempt.save()

                         log_msg = f'  - Bewerteter Versuch für "{exam_for_graded.title}" erstellt.' if created else f'  - Bewerteter Versuch für "{exam_for_graded.title}" aktualisiert.'
                         self.stdout.write(self.style.SUCCESS(log_msg))
                         created_attempts_exams.add(exam_for_graded)
                    
                     except Exception as e: # Aligned with Try Block
                         self.stdout.write(self.style.ERROR(f'  - Fehler beim Erstellen/Aktualisieren des bewerteten Versuchs für {exam_for_graded.title}: {e}'))
                 else: # Aligned with If Block 2
                     self.stdout.write(self.style.WARNING(f'  - Keine Kriterien für Prüfung "{exam_for_graded.title}" gefunden, überspringe bewerteten Versuch.'))
            else: # Aligned with If Block 1
                 self.stdout.write(self.style.WARNING("Keine passende Prüfung für bewerteten Versuch gefunden."))


            # 2. Submitted Attempt 
            exam_for_submitted = None
            possible_submitted_exams = [e for e in exam_list if e not in created_attempts_exams]
            if not possible_submitted_exams:
                 possible_submitted_exams = [e for e in exam_list if not e.modules.exists() and e not in created_attempts_exams]
            
            if possible_submitted_exams: # If Block 3
                 exam_for_submitted = random.choice(possible_submitted_exams)
                 try: # Try Block 2
                     # --- NEU: Voraussetzungen erfüllen ---
                     mark_prerequisites_complete(exam_for_submitted, test_user)
                     # ------------------------------------

                     # Holen oder erstellen
                     submitted_attempt, created = ExamAttempt.objects.get_or_create(
                         exam=exam_for_submitted,
                         user=test_user,
                         defaults={
                             'started_at': timezone.now() - timedelta(days=15),
                             'submitted_at': timezone.now() - timedelta(days=2),
                         }
                     )
                     # Status setzen und speichern
                     submitted_attempt.status = ExamAttempt.Status.SUBMITTED
                     submitted_attempt.submitted_at = timezone.now() - timedelta(days=2) # Sicherstellen
                     submitted_attempt.save()

                     log_msg = f'  - Abgegebener Versuch für "{exam_for_submitted.title}" erstellt.' if created else f'  - Abgegebener Versuch für "{exam_for_submitted.title}" aktualisiert.'
                     self.stdout.write(self.style.SUCCESS(log_msg))
                     created_attempts_exams.add(exam_for_submitted)
                 except Exception as e: # Aligned with Try Block 2
                     self.stdout.write(self.style.ERROR(f'  - Fehler beim Erstellen/Aktualisieren des abgegebenen Versuchs für {exam_for_submitted.title}: {e}'))
            else: # Aligned with If Block 3
                 self.stdout.write(self.style.WARNING("Keine passende Prüfung für abgegebenen Versuch gefunden."))

            # 3. Started Attempt 
            exam_for_started = None
            possible_started_exams = [e for e in exam_list if e not in created_attempts_exams]
            if not possible_started_exams:
                 possible_started_exams = [e for e in exam_list if e.modules.exists() and e not in created_attempts_exams]
            if not possible_started_exams: # This if might be redundant, check logic if needed
                 possible_started_exams = [e for e in exam_list if e not in created_attempts_exams]

            if possible_started_exams: # If Block 4
                 exam_for_started = random.choice(possible_started_exams)
                 try: # Try Block 3
                     # Holen oder erstellen
                     started_attempt, created = ExamAttempt.objects.get_or_create(
                         exam=exam_for_started,
                         user=test_user,
                         defaults={
                             'started_at': timezone.now() - timedelta(days=5),
                         }
                     )
                     # Status setzen und speichern
                     started_attempt.status = ExamAttempt.Status.STARTED
                     started_attempt.started_at = timezone.now() - timedelta(days=5) # Sicherstellen
                     started_attempt.save()

                     log_msg = f'  - Gestarteter Versuch für "{exam_for_started.title}" erstellt.' if created else f'  - Gestarteter Versuch für "{exam_for_started.title}" aktualisiert.'
                     self.stdout.write(self.style.SUCCESS(log_msg))
                     created_attempts_exams.add(exam_for_started)
                 except Exception as e: # Aligned with Try Block 3
                     self.stdout.write(self.style.ERROR(f'  - Fehler beim Erstellen/Aktualisieren des gestarteten Versuchs für {exam_for_started.title}: {e}'))
            else: # Aligned with If Block 4
                self.stdout.write(self.style.WARNING("Keine passende Prüfung für gestarteten Versuch gefunden."))
            
            # Verify available exams count implicitly via view logic later
            
            # --- NEU: Create Certification Paths ---
            if CertificationPath and exam_list: # Nur ausführen, wenn Modell und Prüfungen existieren
                self.stdout.write('Erstelle Zertifikatspfade...')

                # Definition der Pfade: Titel, Beschreibung, Icon, Schlüsselwörter für Prüfungen
                PATH_DEFINITIONS = [
                    {
                        "title": "Frontend Grundlagen",
                        "description": "Der Einstieg in die moderne Frontend-Entwicklung.",
                        "icon": "IoCodeSlashOutline", # Beispiel Icon Name
                        "keywords": ["html", "css", "javascript basics", "react grundlagen", "ui/ux", "layout", "interaktives dashboard"] # Keywords erweitert
                    },
                    {
                        "title": "Python Backend Entwicklung",
                        "description": "Von den Python-Grundlagen zur serverseitigen Entwicklung mit Django.",
                        "icon": "IoServerOutline",
                        "keywords": ["python", "django", "api", "backend", "datenbank", "orm", "webshop", "rest api", "refactoring"] # Keywords erweitert
                    },
                    {
                        "title": "Full-Stack Web Developer",
                        "description": "Umfassender Pfad für die Entwicklung kompletter Webanwendungen.",
                        "icon": "IoLayersOutline",
                        # Umfassendere Keywords
                        "keywords": ["html", "css", "javascript", "react", "next.js", "python", "django", "api", "datenbank", "full-stack", "blog-anwendung"] # Keywords erweitert
                    },
                    {
                         "title": "Datenanalyse mit Python",
                         "description": "Einführung in die Werkzeuge und Techniken der Datenanalyse.",
                         "icon": "IoAnalyticsOutline", # Beispiel, Icon muss im Frontend existieren
                         "keywords": ["datenanalyse", "pandas", "numpy", "matplotlib", "seaborn", "statistik", "pipeline"] # Keywords erweitert
                    },
                    {
                         "title": "DevOps Essentials",
                         "description": "Grundlagen für moderne Softwareentwicklungsprozesse.",
                         "icon": "IoGitBranchOutline", # Beispiel
                         "keywords": ["git", "docker", "linux", "testing", "deployment", "automation", "testsuite", "cloud"] # Keywords erweitert
                    },
                    # Beispiel für einen sehr spezifischen/umfassenden Pfad am Ende
                    {
                         "title": "Python Profi Komplettpaket",
                         "description": "Alle wichtigen Python-Module und Backend-Technologien.",
                         "icon": "IoSchoolOutline", # Beispiel
                         "keywords": ["python", "django", "flask", "api", "test", "oop", "datenbank", "docker", "backend", "rest api"], # Keywords erweitert
                         "order": 99 # Hohe Order, um am Ende zu erscheinen
                    },
                ]

                created_paths_count = 0
                for index, path_def in enumerate(PATH_DEFINITIONS):
                    # Filtere Prüfungen basierend auf Keywords im Titel (case-insensitive)
                    path_exams = []
                    for exam in exam_list:
                        # Prüfe, ob *mindestens ein* Keyword im Titel vorkommt
                        if any(keyword in exam.title.lower() for keyword in path_def["keywords"]):
                            path_exams.append(exam)

                    if not path_exams:
                         self.stdout.write(self.style.WARNING(f'  - Keine passenden Prüfungen für Pfad "{path_def["title"]}" gefunden (Keywords: {path_def["keywords"]}). Überspringe.'))
                         continue

                    # Erstelle oder aktualisiere den Pfad
                    path_obj, created = CertificationPath.objects.get_or_create(
                        title=path_def["title"],
                        defaults={
                            "description": path_def["description"],
                            "icon_name": path_def.get("icon"),
                            "order": path_def.get("order", index * 10) # Default order based on list index
                        }
                    )

                    # Prüfungen zuweisen (alte löschen, neue hinzufügen)
                    path_obj.exams.set(path_exams) # set() ist effizient

                    status_msg = "erstellt" if created else "aktualisiert"
                    self.stdout.write(self.style.SUCCESS(f'  - Zertifikatspfad "{path_obj.title}" {status_msg} mit {len(path_exams)} Prüfung(en).'))
                    created_paths_count += 1

                self.stdout.write(self.style.SUCCESS(f'{created_paths_count} Zertifikatspfade erstellt/aktualisiert.'))

            else:
                 if not CertificationPath:
                     self.stdout.write(self.style.WARNING("CertificationPath Modell nicht verfügbar. Überspringe Pfaderstellung."))
                 if not exam_list:
                      self.stdout.write(self.style.WARNING("Keine Prüfungen zum Zuordnen vorhanden. Überspringe Pfaderstellung."))
                 # Kein else notwendig, da beide oben geprüft werden

        else:
            # Diese Meldung bleibt relevant, da ohne Exams auch keine Paths erstellt werden
            self.stdout.write(self.style.WARNING('Überspringe Prüfungserstellung, Attempt- und Pfad-Generierung, da App nicht verfügbar.'))

        # Abschließende Erfolgsmeldung
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully.')) 