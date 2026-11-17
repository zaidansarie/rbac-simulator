"""
Role-Based Access Control (RBAC) Simulator
Launches the single Web Dashboard directly on http://127.0.0.1:5000
"""

from app import app

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   ROLE-BASED ACCESS CONTROL (RBAC) SIMULATOR")
    print("   Opening Web Dashboard at: http://127.0.0.1:5000")
    print("   Press Ctrl+C to terminate.")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=False)
