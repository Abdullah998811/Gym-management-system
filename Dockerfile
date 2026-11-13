FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for psycopg2 and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
EXPOSE 5000
CMD ["sh", "-c", "flask --app run.py seed && gunicorn --bind 0.0.0.0:${PORT:-5000} run:app"]
