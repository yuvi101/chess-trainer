from celery import Celery
from celery.schedules import crontab

app = Celery(
    "scheduler",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    include=["tasks"]
)

app.conf.broker_connection_retry_on_startup = True
app.conf.timezone = "UTC"

app.conf.beat_schedule = {
    # Runs every Monday and Thursday at 8:00 AM
    "collect-games": {
        "task": "tasks.collect_games",
        "schedule": crontab(hour=7, minute=0, day_of_week="mon,thu"),
    },
    # Runs 30 minutes after collection
    "analyze-games": {
        "task": "tasks.analyze_games",
        "schedule": crontab(hour=7, minute=30, day_of_week="mon,thu"),
    },
}

app.conf.timezone = "UTC"