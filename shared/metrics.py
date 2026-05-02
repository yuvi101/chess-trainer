import os
import logging
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    push_to_gateway
)

PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL", "pushgateway:9091")


def push_metrics(job_name, metrics):
    """
    Push metrics to Prometheus Pushgateway.
    
    metrics is a dict like:
    {
        "games_collected_total": 20,
        "pipeline_failures_total": 0,
    }
    """
    registry = CollectorRegistry()

    for metric_name, value in metrics.items():
        if "duration" in metric_name:
            # Use Histogram for duration metrics
            h = Histogram(
                metric_name,
                f"Metric: {metric_name}",
                registry=registry
            )
            h.observe(value)
        else:
            # Use Counter for everything else
            c = Counter(
                metric_name,
                f"Metric: {metric_name}",
                registry=registry
            )
            c.inc(value)

    try:
        push_to_gateway(PUSHGATEWAY_URL, job=job_name, registry=registry)
        logging.info(f"Metrics pushed to Pushgateway for job: {job_name}")
    except Exception as e:
        logging.warning(f"Failed to push metrics: {e}")