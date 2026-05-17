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
    "run-full-pipeline": {
        "task": "tasks.run_full_pipeline",
        "schedule": crontab(hour=7, minute=0, day_of_week="fri"),
    },
}