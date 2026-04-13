import subprocess
from celery_app import app
import logging

logging.basicConfig(level=logging.INFO)

@app.task
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


@app.task
def analyze_games():
    logging.info("Starting game analysis...")
    result = subprocess.run(
        ["python", "/app/analyzer/game_analyzer.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logging.error(f"Analyzer failed: {result.stderr}")
        raise RuntimeError(result.stderr)
    logging.info("Analysis done.")
    return result.stdout

@app.task
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