FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .


# Create a non-root user
RUN adduser --disabled-password --gecos "" celeryuser \
    && chown -R celeryuser:celeryuser /app

USER celeryuser

CMD ["celery", "-A", "celery_app", "worker", "--beat", "--loglevel=info"]