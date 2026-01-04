import logging
import logging.config
import os

from celery import Celery
from celery.signals import after_setup_logger, after_setup_task_logger, task_postrun, task_prerun

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

app = Celery("tformance")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


# Configure Celery to use Django's logging
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Configure Celery's logger to use Django's logging settings."""
    from django.conf import settings

    # Apply Django logging config
    logging.config.dictConfig(settings.LOGGING)


@after_setup_task_logger.connect
def setup_task_loggers(logger, *args, **kwargs):
    """Configure task logger to use Django's logging settings."""
    from django.conf import settings

    logging.config.dictConfig(settings.LOGGING)


@task_prerun.connect
def task_prerun_handler(task_id, task, *args, **kwargs):
    """Log when a task starts execution."""
    logger = logging.getLogger("celery.task")
    logger.info(f"Task started: {task.name} [{task_id}]")


@task_postrun.connect
def task_postrun_handler(task_id, task, retval, state, *args, **kwargs):
    """Log when a task completes."""
    logger = logging.getLogger("celery.task")
    logger.info(f"Task completed: {task.name} [{task_id}] -> {state}")
