import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_project_nexus.settings")

app = Celery("alx_project_nexus")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
