"""
Role-Based Access Control (RBAC) Simulator - Application Entry Point
"""

from api.index import app, db, engine, auth_service

if __name__ == "__main__":
    print("\nStarting RBAC Simulator Web Server on http://127.0.0.1:5000")
    print("Press Ctrl+C to terminate.")
    app.run(host="127.0.0.1", port=5000, debug=True)
