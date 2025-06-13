#!/usr/bin/env bash
set -o errexit  # Exit on error

echo "🔄 Installing dependencies..."
pip install -r requirements.txt

echo "🔄 Collecting static files..."
python manage.py collectstatic --noinput

echo "🔄 Running database migrations..."
python manage.py migrate

echo "✅ Build completed successfully!"