# Multi-stage build for Django backend
FROM python:3.12-slim as backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Run migrations, create sample users, and start server
CMD python manage.py makemigrations && \
    python manage.py migrate && \
    python manage.py create_sample_users && \
    gunicorn procuretopay.wsgi:application --bind 0.0.0.0:8000 --workers 3

