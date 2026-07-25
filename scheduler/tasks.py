import subprocess
from celery import Task, chain
from celery_app import app
import logging
from shared.notifications import post_to_slack

logging.basicConfig(level=logging.INFO)


class NotifyOnFailureTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        post_to_slack(f":x: `{self.name}` failed after {self.max_retries} retries: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@app.task(base=NotifyOnFailureTask, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)
def collect_games():
    logging.info("Starting game collection...")
    result = subprocess.run(
        ["python", "/app/collector/lichess_collector.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Collector failed: {result.stderr}")
        raise RuntimeError(result.stderr)
    logging.info("Collection done.")
    return result.stdout


@app.task(base=NotifyOnFailureTask, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)
def analyze_games():
    logging.info("Starting game analysis...")
    result = subprocess.run(
        ["python", "/app/analyzer/analyze_game.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Analyzer failed: {result.stderr}")
        raise RuntimeError(result.stderr)
    logging.info("Analysis done.")
    return result.stdout

@app.task(base=NotifyOnFailureTask, autoretry_for=(RuntimeError,), retry_backoff=True, max_retries=3)
def generate_report():
    result = subprocess.run(
        ["python", "/app/reporting/report_generator.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Report generation failed: {result.stderr}")
        raise RuntimeError(result.stderr)
    logging.info("Report generated successfully.")
    return result.stdout


@app.task
def run_full_pipeline():
    logging.info("🚀 Starting full pipeline...")
    chain(
        collect_games.si(),
        analyze_games.si(),
        generate_report.si()
    ).apply_async()
