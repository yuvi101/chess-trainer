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
    # Runs every Friday at 8:00 AM
    "collect-games": {
        "task": "tasks.collect_games",
        "schedule": crontab(hour=7, minute=0, day_of_week="fri"),
    },
    # Runs 30 minutes after collection
    "analyze-games": {
        "task": "tasks.analyze_games",
        "schedule": crontab(hour=7, minute=30, day_of_week="fri"),
    },

    "generate-report": {
    "task": "tasks.generate_report",
    "schedule": crontab(hour=8, minute=0, day_of_week="fri"),  # every Friday morning
},
}

app.conf.timezone = "UTC"