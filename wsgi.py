"""WSGI entry point for production servers (gunicorn).

Run with:
    gunicorn wsgi:app

The app reads all configuration from environment variables in production
(see DEPLOY.md), falling back to config.py for local development.
"""
from app import create_app

app = create_app()
