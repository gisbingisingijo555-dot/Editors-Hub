from django.apps import AppConfig

class EditorsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'EditorsApp'

    def ready(self):
        import EditorsApp.signals