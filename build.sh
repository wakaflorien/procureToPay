#!/bin/bash
# Build script for Render deployment
# This script handles migrations and static file collection

set -e  # Exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Build completed successfully!"

