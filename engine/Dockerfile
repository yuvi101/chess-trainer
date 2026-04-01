FROM python:3.11-slim

WORKDIR /app

# Install system deps if ever needed (good practice)
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# requirements.txt is inside engine/ folder
COPY . .

CMD ["python", "analyze_game.py"]