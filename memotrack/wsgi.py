"""
WSGI config for memotrack project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

# Add the project root directory to the sys.path
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if path not in sys.path:
    sys.path.insert(0, path)

# Debug: Print directory contents to Vercel logs
print(f"WSGI: Current directory: {os.getcwd()}")
print(f"WSGI: Project path: {path}")
print(f"WSGI: Directory contents: {os.listdir(path)}")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'memotrack.settings')

application = get_wsgi_application()
app = application
