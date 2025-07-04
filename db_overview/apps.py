from django.apps import AppConfig


class DbOverviewConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'db_overview'
    verbose_name = 'Database Overview'
