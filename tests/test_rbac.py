"""
Unit Tests for RBAC Simulator
Covers:
- Salted SHA-256 Authentication & Account Lockout
- Distinction between Authentication & Authorization
- Role-Based Access Control PEP / PDP decisions
- Least Privilege enforcement on Admin, Teacher, Student
- Audit Logging of Allowed and Denied attempts
"""

import unittest
from datetime import datetime
from rbac.models import Role, Permission, User
from rbac.core import RBACEngine, AccessDeniedError
from rbac.auth import AuthenticationService
from rbac.database import Database


class TestRBACAuthentication(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.auth = AuthenticationService(lockout_threshold=3, lockout_minutes=5)

    def test_passwords_are_not_plaintext(self):
        """Verify that stored passwords are cryptographically salted SHA-256 hashes, not plaintext."""
        for username, user in self.db.users.items():
            self.assertNotEqual(user.password_hash, self.db.DEFAULT_PASSWORDS.get(username))
            self.assertTrue(len(user.password_hash) == 64, "PBKDF2-HMAC-SHA256 hex string should be 64 characters")
            self.assertTrue(len(user.salt) >= 16, "Salt should be at least 16 hex characters")

    def test_successful_authentication(self):
        """Valid credentials return a session token and user object."""
        success, msg, token, user = self.auth.authenticate(
            "prof_sharma", self.db.DEFAULT_PASSWORDS["prof_sharma"], self.db.users
        )
        self.assertTrue(success)
        self.assertIsNotNone(token)
        self.assertIsNotNone(user)
        self.assertEqual(user.role, Role.TEACHER)

    def test_invalid_password_authentication(self):
        """Invalid password fails authentication without issuing a session token."""
        success, msg, token, user = self.auth.authenticate(
            "prof_sharma", "WrongPassword123!", self.db.users
        )
        self.assertFalse(success)
        self.assertIsNone(token)
        self.assertIn("Invalid credentials", msg)

    def test_account_lockout_after_three_failed_attempts(self):
        """Account is locked after 3 consecutive failed login attempts."""
        username = "student_neha"
        for _ in range(3):
            self.auth.authenticate(username, "WrongPass!", self.db.users)
        
        user = self.db.users[username]
        self.assertTrue(user.is_locked())

        # Attempt with correct password should still be blocked while locked
        success, msg, token, _ = self.auth.authenticate(
            username, self.db.DEFAULT_PASSWORDS[username], self.db.users
        )
        self.assertFalse(success)
        self.assertIn("Account locked", msg)


class TestRBACAuthorization(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.engine = RBACEngine()
        self.admin = self.db.users["admin"]
        self.teacher = self.db.users["prof_sharma"]
        self.student = self.db.users["student_rohit"]

    def test_admin_permissions(self):
        """Admin has full CRUD permissions: View, Add, Edit, Delete, plus Audit & User Management."""
        for perm in [
            Permission.VIEW_RECORD,
            Permission.ADD_RECORD,
            Permission.EDIT_RECORD,
            Permission.DELETE_RECORD,
            Permission.VIEW_AUDIT_LOGS,
            Permission.MANAGE_USERS,
        ]:
            decision = self.engine.evaluate(self.admin, perm)
            self.assertTrue(decision.allowed, f"Admin should have permission: {perm.value}")
            # PEP should not raise
            self.engine.enforce(self.admin, perm)

    def test_teacher_permissions_and_least_privilege(self):
        """Teacher can View, Add, and Edit records, but CANNOT Delete records."""
        # Allowed
        for perm in [Permission.VIEW_RECORD, Permission.ADD_RECORD, Permission.EDIT_RECORD]:
            decision = self.engine.evaluate(self.teacher, perm)
            self.assertTrue(decision.allowed, f"Teacher should have permission: {perm.value}")
            self.engine.enforce(self.teacher, perm)

        # Denied (Least Privilege)
        for perm in [Permission.DELETE_RECORD, Permission.VIEW_AUDIT_LOGS, Permission.MANAGE_USERS]:
            decision = self.engine.evaluate(self.teacher, perm)
            self.assertFalse(decision.allowed, f"Teacher should NOT have permission: {perm.value}")
            with self.assertRaises(AccessDeniedError):
                self.engine.enforce(self.teacher, perm)

    def test_student_permissions_and_least_privilege(self):
        """Student has Read-only access: can View records, but CANNOT Add, Edit, or Delete records."""
        # Allowed
        decision = self.engine.evaluate(self.student, Permission.VIEW_RECORD)
        self.assertTrue(decision.allowed, "Student should be permitted to view records")
        self.engine.enforce(self.student, Permission.VIEW_RECORD)

        # Denied
        for perm in [
            Permission.ADD_RECORD,
            Permission.EDIT_RECORD,
            Permission.DELETE_RECORD,
            Permission.VIEW_AUDIT_LOGS,
            Permission.MANAGE_USERS,
        ]:
            decision = self.engine.evaluate(self.student, perm)
            self.assertFalse(decision.allowed, f"Student should NOT have permission: {perm.value}")
            with self.assertRaises(AccessDeniedError):
                self.engine.enforce(self.student, perm)

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests must be denied at PEP."""
        decision = self.engine.evaluate(None, Permission.VIEW_RECORD)
        self.assertFalse(decision.allowed)
        with self.assertRaises(AccessDeniedError):
            self.engine.enforce(None, Permission.VIEW_RECORD)


class TestAuditLogging(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.engine = RBACEngine()
        self.student = self.db.users["student_rohit"]

    def test_audit_log_captures_denied_attempt(self):
        """Denied authorization attempts are properly captured in the security audit log."""
        try:
            self.engine.enforce(self.student, Permission.DELETE_RECORD, resource_id="REC-101")
        except AccessDeniedError as e:
            entry = self.db.log_audit(
                username=self.student.username,
                role=self.student.role.value,
                action=Permission.DELETE_RECORD.value,
                resource_id="REC-101",
                status="DENIED",
                reason=e.message
            )
            self.assertEqual(entry.status, "DENIED")
            self.assertEqual(entry.username, "student_rohit")
            self.assertIn("Least Privilege", entry.reason)

        latest_logs = self.db.list_audit_logs(limit=1, status_filter="DENIED")
        self.assertEqual(len(latest_logs), 1)
        self.assertEqual(latest_logs[0].status, "DENIED")


if __name__ == "__main__":
    unittest.main()
