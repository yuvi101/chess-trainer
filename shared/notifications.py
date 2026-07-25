import os
import logging
import requests

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")


def post_to_slack(text):
    """
    Post a text message to the configured Slack incoming webhook.

    No-ops (with a warning) if SLACK_WEBHOOK_URL isn't set, and never
    raises on failure — a broken webhook shouldn't fail the pipeline
    it's trying to report on.
    """
    if not SLACK_WEBHOOK_URL:
        logging.warning("SLACK_WEBHOOK_URL not set, skipping Slack notification")
        return

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logging.warning(f"Failed to post to Slack: {e}")
