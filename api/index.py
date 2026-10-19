"""
Vercel Serverless Function entrypoint for SubFynn Web App.
Routes incoming HTTP requests to AppRequestHandler.
"""

import os
import sys

# Ensure project root directory is on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from app import AppRequestHandler

    class handler(AppRequestHandler):
        """
        Vercel Python serverless handler using AppRequestHandler.
        """
        pass

except Exception as err:
    from http.server import BaseHTTPRequestHandler
    import json

    class handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "online",
                        "app": "SubFynn AI Thai Subtitle Generator",
                        "error_fallback": str(err),
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            )
