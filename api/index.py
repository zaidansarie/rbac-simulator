"""
Role-Based Access Control (RBAC) Simulator - Vercel Serverless Entrypoint
Self-contained module with templates, static assets, and RBAC policy enforcement.
"""

import os
import sys
import secrets
import traceback
from typing import Optional
from flask import Flask, render_template, request, jsonify, session

# Resolve local and parent directories for sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))

for p in [current_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from rbac.models import Role, Permission, User
from rbac.core import RBACEngine, AccessDeniedError
from rbac.auth import AuthenticationService
from rbac.database import Database
from verify_rbac import PermissionsMatrixVerifier
from embedded_assets import EMBEDDED_TEMPLATES, EMBEDDED_STATIC
from jinja2 import ChoiceLoader, FileSystemLoader, DictLoader

# Bulletproof template and static directory discovery
template_candidates = [
    os.path.join(current_dir, "templates"),
    os.path.join(root_dir, "templates"),
    os.path.abspath("templates"),
    os.path.abspath("api/templates")
]
template_dir = next((d for d in template_candidates if os.path.isdir(d)), os.path.join(current_dir, "templates"))

static_candidates = [
    os.path.join(current_dir, "static"),
    os.path.join(root_dir, "static"),
    os.path.abspath("static"),
    os.path.abspath("api/static")
]
static_dir = next((d for d in static_candidates if os.path.isdir(d)), os.path.join(current_dir, "static"))

app = Flask(
    __name__,
    template_folder=template_dir,
    static_folder=static_dir
)
app.secret_key = os.environ.get("SECRET_KEY", "rbac-super-secret-cryptography-pbl-key-2024")

# Configure Jinja ChoiceLoader: checks disk first, seamlessly falls back to embedded strings
loaders = []
if os.path.isdir(template_dir):
    loaders.append(FileSystemLoader(template_dir))
if os.path.isdir(os.path.join(root_dir, "templates")):
    loaders.append(FileSystemLoader(os.path.join(root_dir, "templates")))
loaders.append(DictLoader(EMBEDDED_TEMPLATES))
app.jinja_loader = ChoiceLoader(loaders)

# Global Singletons
db = Database()
engine = RBACEngine()
auth_service = AuthenticationService()


def get_current_user() -> Optional[User]:
    """Helper to retrieve user from session with fallback support for serverless."""
    token = session.get("session_token")
    if token:
        user = auth_service.get_user_from_session(token, db.users)
        if user:
            return user
    username = session.get("username")
    if username and username in db.users:
        return db.users[username]
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


@app.errorhandler(Exception)
def handle_exception(e):
    """Graceful error handler to return diagnostic info instead of crashing the function."""
    app.logger.error("Unhandled Exception: %s\n%s", str(e), traceback.format_exc())
    if request.path.startswith("/api/"):
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500
    return f"<h1>500 Internal Error</h1><p>{str(e)}</p><pre>{traceback.format_exc()}</pre>", 500


# ==========================================
# Frontend Routes & Healthchecks
# ==========================================

@app.route("/ping")
def ping():
    """Healthcheck endpoint for monitoring serverless cold-start readiness."""
    return jsonify({
        "status": "healthy",
        "current_dir": current_dir,
        "users_count": len(db.users),
        "records_count": len(db.records),
        "embedded_templates": list(EMBEDDED_TEMPLATES.keys()),
        "embedded_static": list(EMBEDDED_STATIC.keys())
    })


@app.route("/static/<path:filename>")
def custom_static(filename):
    """Resilient static file server with embedded fallback."""
    file_path = os.path.join(static_dir, filename)
    if os.path.isfile(file_path):
        from flask import send_from_directory
        return send_from_directory(static_dir, filename)
    if filename in EMBEDDED_STATIC:
        mimetype = "text/css" if filename.endswith(".css") else "application/javascript"
        from flask import Response
        return Response(EMBEDDED_STATIC[filename], mimetype=mimetype)
    return "File not found", 404


@app.route("/")
def index():
    user = get_current_user()
    if not user:
        # Default auto-login as Admin with zero PBKDF2 compute overhead
        admin_user = db.users.get("admin")
        if admin_user:
            token = secrets.token_hex(24)
            auth_service.active_sessions[token] = "admin"
            session["session_token"] = token
            session["username"] = "admin"
            user = admin_user

    records = db.list_records()
    return render_template("index.html", records=records, active_page="dashboard")


@app.route("/matrix")
def matrix_view():
    matrix_data = engine.get_matrix_data()
    return render_template("matrix.html", matrix_data=matrix_data, active_page="matrix")


@app.route("/audit")
def audit_view():
    user = get_current_user()
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
        session["username"] = user.username
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
    session.pop("username", None)
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


# Export both app and application for WSGI compatibility on Vercel
application = app

