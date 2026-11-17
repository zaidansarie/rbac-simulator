"""
RBAC Simulator - Main Application Entrypoint
Zero-configuration deployment entry for Vercel and local runtimes.
"""

from app import app

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
