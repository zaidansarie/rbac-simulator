"""
Role-Based Access Control (RBAC) Simulator - Flask Web Application
Features:
- Live multi-role simulator (Admin, Teacher, Student)
- CRUD operations with Policy Enforcement Point (PEP) checks
- Visual Permissions Matrix & PDP Decision Evaluator
- Real-time Security Audit Log
- One-click Independent Verification Suite Runner
"""

from flask import Flask, render_template, request, jsonify, session
from typing import Optional
from rbac.models import Role, Permission, User
from rbac.core import RBACEngine, AccessDeniedError
from rbac.auth import AuthenticationService
from rbac.database import Database
from verify_rbac import PermissionsMatrixVerifier

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.secret_key = os.environ.get("SECRET_KEY", "rbac-super-secret-cryptography-pbl-key-2024")

# Global Singletons
db = Database()
engine = RBACEngine()
auth_service = AuthenticationService()


def get_current_user() -> Optional[User]:
    """Helper to retrieve user from Flask session."""
    token = session.get("session_token")
    if token:
        user = auth_service.get_user_from_session(token, db.users)
        if user:
            return user
    return None


@app.context_processor
def inject_user_context():
    user = get_current_user()
    perms = [p.value for p in engine.get_permissions_for_role(user.role)] if user else []
    return {
        "current_user": user,
        "user_permissions": perms,
        "all_roles": [r.value for r in Role]
    }


# ==========================================
# Frontend Page Routes
# ==========================================

@app.route("/")
def index():
    user = get_current_user()
    if not user:
        # Default auto-login as Admin for seamless initial exploration
        _, _, token, u = auth_service.authenticate("admin", db.DEFAULT_PASSWORDS["admin"], db.users)
        session["session_token"] = token
        user = u

    records = db.list_records()
    return render_template("index.html", records=records, active_page="dashboard")


@app.route("/matrix")
def matrix_view():
    matrix_data = engine.get_matrix_data()
    return render_template("matrix.html", matrix_data=matrix_data, active_page="matrix")


@app.route("/audit")
def audit_view():
    user = get_current_user()
    # Check if user has permission to view audit logs
    has_perm = user and engine.has_permission(user.role, Permission.VIEW_AUDIT_LOGS)
    logs = db.list_audit_logs(limit=100) if has_perm else []
    return render_template("audit.html", logs=logs, has_perm=has_perm, active_page="audit")


@app.route("/verify")
def verify_view():
    return render_template("verify.html", active_page="verify")


# ==========================================
# REST API Endpoints
# ==========================================

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "")

    # Quick role login option
    quick_role = data.get("quick_role")
    if quick_role:
        role_map = {
            "Admin": ("admin", db.DEFAULT_PASSWORDS["admin"]),
            "Teacher": ("prof_sharma", db.DEFAULT_PASSWORDS["prof_sharma"]),
            "Student": ("student_rohit", db.DEFAULT_PASSWORDS["student_rohit"]),
        }
        if quick_role in role_map:
            username, password = role_map[quick_role]

    success, msg, token, user = auth_service.authenticate(username, password, db.users)
    ip = request.remote_addr or "127.0.0.1"

    if success:
        session["session_token"] = token
        db.log_audit(
            username=user.username,
            role=user.role.value,
            action="auth:login",
            resource_id=None,
            status="ALLOWED",
            reason=msg,
            ip_address=ip
        )
        return jsonify({
            "success": True,
            "message": msg,
            "user": user.to_dict(),
            "permissions": [p.value for p in engine.get_permissions_for_role(user.role)]
        })
    else:
        db.log_audit(
            username=username or "unknown",
            role=user.role.value if user else "None",
            action="auth:login",
            resource_id=None,
            status="DENIED",
            reason=msg,
            ip_address=ip
        )
        return jsonify({"success": False, "message": msg}), 401


@app.route("/api/logout", methods=["POST"])
def api_logout():
    token = session.get("session_token")
    if token:
        auth_service.logout(token)
        session.pop("session_token", None)
    return jsonify({"success": True, "message": "Logged out successfully."})


@app.route("/api/current-user", methods=["GET"])
def api_current_user():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({
        "authenticated": True,
        "user": user.to_dict(),
        "permissions": [p.value for p in engine.get_permissions_for_role(user.role)]
    })


@app.route("/api/records", methods=["GET"])
def api_get_records():
    user = get_current_user()
    ip = request.remote_addr or "127.0.0.1"
    try:
        engine.enforce(user, Permission.VIEW_RECORD)
        records = [r.to_dict() for r in db.list_records()]
        db.log_audit(
            username=user.username,
            role=user.role.value,
            action=Permission.VIEW_RECORD.value,
            resource_id="ALL",
            status="ALLOWED",
            reason="Queried all academic records list",
            ip_address=ip
        )
        return jsonify({"success": True, "records": records})
    except AccessDeniedError as e:
        db.log_audit(
            username=user.username if user else "anonymous",
            role=user.role.value if user else "None",
            action=Permission.VIEW_RECORD.value,
            resource_id="ALL",
            status="DENIED",
            reason=e.message,
            ip_address=ip
        )
        return jsonify({"success": False, "error": e.message}), 403


@app.route("/api/records", methods=["POST"])
def api_add_record():
    user = get_current_user()
    ip = request.remote_addr or "127.0.0.1"
    try:
        # Enforce ADD_RECORD permission
        engine.enforce(user, Permission.ADD_RECORD)

        data = request.get_json() or {}
        student_id = data.get("student_id", "").strip()
        student_name = data.get("student_name", "").strip()
        course = data.get("course", "").strip()
        grade = data.get("grade", "A").strip()
        attendance = float(data.get("attendance", 85.0))
        remarks = data.get("remarks", "").strip()

        if not student_id or not student_name or not course:
            return jsonify({"success": False, "error": "Missing required fields."}), 400

        record = db.create_record(
            student_id=student_id,
            student_name=student_name,
            course=course,
            grade=grade,
            attendance=attendance,
            remarks=remarks,
            created_by=user.username
        )

        db.log_audit(
            username=user.username,
            role=user.role.value,
            action=Permission.ADD_RECORD.value,
            resource_id=record.record_id,
            status="ALLOWED",
            reason=f"Created academic record {record.record_id} for student '{student_name}'",
            ip_address=ip
        )
        return jsonify({"success": True, "record": record.to_dict()})
    except AccessDeniedError as e:
        db.log_audit(
            username=user.username if user else "anonymous",
            role=user.role.value if user else "None",
            action=Permission.ADD_RECORD.value,
            resource_id=None,
            status="DENIED",
            reason=e.message,
            ip_address=ip
        )
        return jsonify({
            "success": False,
            "error": e.message,
            "security_context": {
                "required_permission": Permission.ADD_RECORD.value,
                "current_role": user.role.value if user else "Unauthenticated",
                "least_privilege_note": "Students lack record creation authority to prevent academic grade tampering."
            }
        }), 403


@app.route("/api/records/<record_id>", methods=["PUT"])
def api_edit_record(record_id: str):
    user = get_current_user()
    ip = request.remote_addr or "127.0.0.1"
    try:
        # Enforce EDIT_RECORD permission
        engine.enforce(user, Permission.EDIT_RECORD, resource_id=record_id)

        data = request.get_json() or {}
        record = db.update_record(
            record_id=record_id,
            course=data.get("course"),
            grade=data.get("grade"),
            attendance=float(data["attendance"]) if "attendance" in data else None,
            remarks=data.get("remarks"),
            modified_by=user.username
        )

        if not record:
            return jsonify({"success": False, "error": f"Record {record_id} not found."}), 404

        db.log_audit(
            username=user.username,
            role=user.role.value,
            action=Permission.EDIT_RECORD.value,
            resource_id=record_id,
            status="ALLOWED",
            reason=f"Modified grade/attendance on {record_id}",
            ip_address=ip
        )
        return jsonify({"success": True, "record": record.to_dict()})
    except AccessDeniedError as e:
        db.log_audit(
            username=user.username if user else "anonymous",
            role=user.role.value if user else "None",
            action=Permission.EDIT_RECORD.value,
            resource_id=record_id,
            status="DENIED",
            reason=e.message,
            ip_address=ip
        )
        return jsonify({
            "success": False,
            "error": e.message,
            "security_context": {
                "required_permission": Permission.EDIT_RECORD.value,
                "current_role": user.role.value if user else "Unauthenticated",
                "least_privilege_note": "Students are unauthorized to modify grade reports or attendance data."
            }
        }), 403


@app.route("/api/records/<record_id>", methods=["DELETE"])
def api_delete_record(record_id: str):
    user = get_current_user()
    ip = request.remote_addr or "127.0.0.1"
    try:
        # Enforce DELETE_RECORD permission
        engine.enforce(user, Permission.DELETE_RECORD, resource_id=record_id)

        rec = db.get_record(record_id)
        if not rec:
            return jsonify({"success": False, "error": f"Record {record_id} not found."}), 404

        db.delete_record(record_id)
        db.log_audit(
            username=user.username,
            role=user.role.value,
            action=Permission.DELETE_RECORD.value,
            resource_id=record_id,
            status="ALLOWED",
            reason=f"Record {record_id} permanently deleted by {user.username}",
            ip_address=ip
        )
        return jsonify({"success": True, "message": f"Record {record_id} deleted."})
    except AccessDeniedError as e:
        db.log_audit(
            username=user.username if user else "anonymous",
            role=user.role.value if user else "None",
            action=Permission.DELETE_RECORD.value,
            resource_id=record_id,
            status="DENIED",
            reason=e.message,
            ip_address=ip
        )
        return jsonify({
            "success": False,
            "error": e.message,
            "security_context": {
                "required_permission": Permission.DELETE_RECORD.value,
                "current_role": user.role.value if user else "Unauthenticated",
                "least_privilege_note": "Record deletion is an administrative action reserved solely for Admin. Teachers and Students are strictly restricted."
            }
        }), 403


@app.route("/api/matrix", methods=["GET"])
def api_get_matrix():
    return jsonify(engine.get_matrix_data())


@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    """Policy Decision Point (PDP) interactive evaluation endpoint."""
    data = request.get_json() or {}
    role_str = data.get("role", "Student")
    action_str = data.get("action", "record:view")

    try:
        role = Role.from_string(role_str)
        perm = Permission(action_str)
        allowed = engine.has_permission(role, perm)
        reason = (
            f"Granted: Role '{role.value}' possesses '{perm.value}'"
            if allowed
            else f"Denied: Role '{role.value}' lacks '{perm.value}'. Least privilege enforced."
        )
        return jsonify({
            "role": role.value,
            "action": perm.value,
            "allowed": allowed,
            "reason": reason
        })
    except ValueError as ex:
        return jsonify({"error": str(ex)}), 400


@app.route("/api/audit-logs", methods=["GET"])
def api_get_audit_logs():
    user = get_current_user()
    try:
        engine.enforce(user, Permission.VIEW_AUDIT_LOGS)
        logs = [l.to_dict() for l in db.list_audit_logs(limit=100)]
        return jsonify({"success": True, "logs": logs})
    except AccessDeniedError as e:
        return jsonify({
            "success": False,
            "error": e.message,
            "note": "Only Admin users are authorized to inspect security audit logs."
        }), 403


@app.route("/api/verify", methods=["GET", "POST"])
def api_run_verify():
    """Runs the independent matrix verification suite."""
    verifier = PermissionsMatrixVerifier()
    summary = verifier.run_all_tests(verbose=False)
    return jsonify(summary)


@app.route("/api/reset", methods=["POST"])
def api_reset():
    user = get_current_user()
    if not user or user.role != Role.ADMIN:
        return jsonify({"success": False, "error": "Only Admin can reset the database."}), 403
    db.reset_to_defaults()
    return jsonify({"success": True, "message": "Database reset to factory default records and users."})


if __name__ == "__main__":
    print("\nStarting RBAC Simulator Web Server on http://127.0.0.1:5000")
    print("Press Ctrl+C to terminate.")
    app.run(host="127.0.0.1", port=5000, debug=True)
