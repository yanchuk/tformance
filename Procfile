# Heroku Procfile - Process definitions for Heroku deployment
# See: https://devcenter.heroku.com/articles/procfile

# Release phase - runs on every deploy before new dynos start
# Handles database migrations and Celery task bootstrapping
release: python manage.py migrate --noinput && python manage.py bootstrap_celery_tasks --remove-stale

# Web process - serves the Django application via gunicorn + uvicorn
web: gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 tformance.asgi:application -k uvicorn.workers.UvicornWorker

# Worker process - handles background Celery tasks
worker: celery -A tformance worker -l INFO --pool threads --concurrency 10 -Q celery,sync,compute,llm

# Beat process - schedules periodic tasks (only run ONE instance)
beat: celery -A tformance beat -l INFO
