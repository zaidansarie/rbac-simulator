"""
Vercel Serverless Function Entry Point for RBAC Simulator
"""

import sys
import os
import traceback

# Ensure the root directory and api directory are in sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

try:
    from app import app
except Exception as e:
    from flask import Flask
    app = Flask(__name__)
    tb = traceback.format_exc()

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def error_fallback(path):
        return f"""
        <div style="font-family:sans-serif;padding:30px;max-width:800px;margin:auto;">
            <h2 style="color:#dc2626;">Vercel Deployment Startup Error</h2>
            <p>An exception occurred while importing the Flask application:</p>
            <pre style="background:#f1f5f9;padding:15px;border-radius:8px;border:1px solid #cbd5e1;overflow:auto;">{tb}</pre>
        </div>
        """, 500
