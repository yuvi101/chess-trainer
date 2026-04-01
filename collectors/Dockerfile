FROM python:3.11-slim

WORKDIR /app

# Install system deps if ever needed (good practice)
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY only the files in collectors/ into /app
COPY . .

CMD ["python", "lichess_collector.py"]