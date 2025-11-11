import os

from django.core.wsgi import get_wsgi_application

# Ensure Django settings are configured for the serverless environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

# Expose WSGI application as `app` for Vercel Python runtime
app = get_wsgi_application()


