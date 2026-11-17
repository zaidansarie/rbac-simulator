"""
Flask Web Application & API Integration Tests
Tests all endpoints, role switching, permissions matrix, and PEP enforcement.
"""

import unittest
import json
from app import app, db


class TestRBACWebApplication(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.client.testing = True
        db.reset_to_defaults()

    def test_dashboard_route_loads(self):
        """Dashboard renders successfully with records."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"RBAC Simulator", response.data)
        self.assertIn(b"Academic Records", response.data)

    def test_audit_logs_permission_enforcement(self):
        """Student cannot view audit logs (403), while Admin can view them."""
        # Log in as Student
        self.client.post("/api/login", json={"quick_role": "Student"})
        res_student = self.client.get("/api/audit-logs")
        self.assertEqual(res_student.status_code, 403)

        # Log in as Admin
        self.client.post("/api/login", json={"quick_role": "Admin"})
        res_admin = self.client.get("/api/audit-logs")
        self.assertEqual(res_admin.status_code, 200)
        data = json.loads(res_admin.data)
        self.assertTrue(data["success"])

    def test_student_cannot_add_or_delete_record(self):
        """Student attempting to add or delete records is denied with 403 Forbidden."""
        # Log in as Student
        self.client.post("/api/login", json={"quick_role": "Student"})

        # Try to Add Record
        add_res = self.client.post("/api/records", json={
            "student_id": "STU-9999",
            "student_name": "Unauthorized Add",
            "course": "Cryptography",
            "grade": "A+",
            "attendance": 100,
            "remarks": "Fake entry"
        })
        self.assertEqual(add_res.status_code, 403)

        # Try to Delete Record
        del_res = self.client.delete("/api/records/REC-101")
        self.assertEqual(del_res.status_code, 403)

    def test_teacher_can_edit_but_cannot_delete(self):
        """Teacher can edit grade/attendance, but CANNOT delete a record."""
        # Log in as Teacher
        self.client.post("/api/login", json={"quick_role": "Teacher"})

        # Edit should succeed
        edit_res = self.client.put("/api/records/REC-101", json={
            "grade": "A+",
            "attendance": 99.0,
            "remarks": "Updated by Teacher"
        })
        self.assertEqual(edit_res.status_code, 200)

        # Delete should fail (403 Forbidden)
        del_res = self.client.delete("/api/records/REC-101")
        self.assertEqual(del_res.status_code, 403)

    def test_admin_can_delete_record(self):
        """Admin is authorized to delete records."""
        # Log in as Admin
        self.client.post("/api/login", json={"quick_role": "Admin"})

        # Delete should succeed
        del_res = self.client.delete("/api/records/REC-105")
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(db.get_record("REC-105"))

    def test_verify_api_endpoint(self):
        """Verify API executes the full matrix verification suite."""
        res = self.client.post("/api/verify")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["total_tests"], 18)
        self.assertEqual(data["passed_tests"], 18)
        self.assertTrue(data["all_passed"])


if __name__ == "__main__":
    unittest.main()
