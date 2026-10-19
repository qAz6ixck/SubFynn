"""
Vercel Serverless Function entrypoint for SubFynn Web App.
Routes incoming HTTP requests to AppRequestHandler or WSGI application.
"""

import os
import sys

# Ensure project root directory is on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app import AppRequestHandler, WSGIApp, wsgi_application

# Top-level class definition for Vercel BaseHTTPRequestHandler detection
class handler(AppRequestHandler):
    """
    Vercel Python serverless handler using AppRequestHandler.
    """
    pass


# Top-level callable variables for Vercel WSGI/ASGI entrypoint detection
app = wsgi_application
application = wsgi_application
