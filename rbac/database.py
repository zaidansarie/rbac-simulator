"""
Role-Based Access Control (RBAC) Simulator - Database & Data Repository
Handles in-memory storage of Users, Academic Records, and Security Audit Logs.
All fictional accounts and records use Indian names.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional
from rbac.models import User, Role, AcademicRecord, AuditLog
from rbac.auth import AuthenticationService


class Database:
    """
    In-memory data store with predefined dummy accounts and academic records.
    Provides reset functionality for reliable independent verification runs.
    """

    DEFAULT_PASSWORDS = {
        "admin": "AdminPassword123!",
        "prof_sharma": "TeacherPass123!",
        "dr_priya": "TeacherPass123!",
        "student_rohit": "StudentPass123!",
        "student_neha": "StudentPass123!",
        "student_ananya": "StudentPass123!",
    }

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.records: Dict[str, AcademicRecord] = {}
        self.audit_logs: List[AuditLog] = []
        self.reset_to_defaults()

    def reset_to_defaults(self):
        """Initializes default fictional accounts, records, and clears logs."""
        self.users.clear()
        self.records.clear()
        self.audit_logs.clear()

        # Seed Users with Salted SHA-256 Hashes (All Indian Names)
        self._add_user("admin", "Aarav Sharma (System Admin)", Role.ADMIN, self.DEFAULT_PASSWORDS["admin"])
        self._add_user("prof_sharma", "Prof. Rajesh Sharma", Role.TEACHER, self.DEFAULT_PASSWORDS["prof_sharma"])
        self._add_user("dr_priya", "Dr. Priya Patel", Role.TEACHER, self.DEFAULT_PASSWORDS["dr_priya"])
        self._add_user("student_rohit", "Rohit Verma", Role.STUDENT, self.DEFAULT_PASSWORDS["student_rohit"], student_id="STU-1001")
        self._add_user("student_neha", "Neha Kulkarni", Role.STUDENT, self.DEFAULT_PASSWORDS["student_neha"], student_id="STU-1002")
        self._add_user("student_ananya", "Ananya Iyer", Role.STUDENT, self.DEFAULT_PASSWORDS["student_ananya"], student_id="STU-1003")

        # Seed Academic Records (All Indian Names)
        records_data = [
            ("REC-101", "STU-1001", "Rohit Verma", "Applied Cryptography & Network Security", "A", 96.5, "Outstanding performance in symmetric encryption labs.", "prof_sharma"),
            ("REC-102", "STU-1002", "Neha Kulkarni", "Authentication & Access Control Architectures", "B+", 87.0, "Good grasp of RBAC; needs revision on PKI.", "prof_sharma"),
            ("REC-103", "STU-1003", "Ananya Iyer", "Cloud Security & Cryptographic Protocols", "A-", 91.5, "Strong analytical submission on TLS handshakes.", "dr_priya"),
            ("REC-104", "STU-1004", "Aditya Verma", "Ethical Hacking & Defense Countermeasures", "A+", 98.0, "Flawless score in firewall packet rule analysis.", "prof_sharma"),
            ("REC-105", "STU-1005", "Diya Patel", "Information Security Principles", "B", 82.0, "Consistent attendance and active participation in seminars.", "dr_priya"),
        ]

        for rec_id, s_id, s_name, course, grade, att, rem, created_by in records_data:
            self.records[rec_id] = AcademicRecord(
                record_id=rec_id,
                student_id=s_id,
                student_name=s_name,
                course=course,
                grade=grade,
                attendance=att,
                remarks=rem,
                created_by=created_by,
                last_modified_by=created_by,
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # Initial System Audit Log Entry
        self.log_audit(
            username="system",
            role="System",
            action="system:init",
            resource_id="db",
            status="ALLOWED",
            reason="Database initialized with 3 Roles, 6 Users, and 5 Academic Records.",
            ip_address="127.0.0.1"
        )

    def _add_user(self, username: str, full_name: str, role: Role, password: str, student_id: Optional[str] = None):
        hash_hex, salt = AuthenticationService.hash_password(password)
        self.users[username.lower()] = User(
            username=username.lower(),
            full_name=full_name,
            role=role,
            password_hash=hash_hex,
            salt=salt,
            student_id=student_id,
            is_active=True
        )

    # --- Academic Records Operations ---

    def list_records(self) -> List[AcademicRecord]:
        return list(self.records.values())

    def get_record(self, record_id: str) -> Optional[AcademicRecord]:
        return self.records.get(record_id)

    def create_record(
        self,
        student_id: str,
        student_name: str,
        course: str,
        grade: str,
        attendance: float,
        remarks: str,
        created_by: str,
        record_id: Optional[str] = None
    ) -> AcademicRecord:
        if not record_id:
            existing_nums = [
                int(k.split("-")[1]) for k in self.records.keys() if k.startswith("REC-") and k.split("-")[1].isdigit()
            ]
            next_num = max(existing_nums, default=100) + 1
            record_id = f"REC-{next_num}"

        record = AcademicRecord(
            record_id=record_id,
            student_id=student_id,
            student_name=student_name,
            course=course,
            grade=grade,
            attendance=attendance,
            remarks=remarks,
            created_by=created_by,
            last_modified_by=created_by,
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.records[record_id] = record
        return record

    def update_record(
        self,
        record_id: str,
        course: Optional[str] = None,
        grade: Optional[str] = None,
        attendance: Optional[float] = None,
        remarks: Optional[str] = None,
        modified_by: str = "unknown"
    ) -> Optional[AcademicRecord]:
        record = self.records.get(record_id)
        if not record:
            return None

        if course is not None:
            record.course = course
        if grade is not None:
            record.grade = grade
        if attendance is not None:
            record.attendance = attendance
        if remarks is not None:
            record.remarks = remarks

        record.last_modified_by = modified_by
        record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return record

    def delete_record(self, record_id: str) -> bool:
        if record_id in self.records:
            del self.records[record_id]
            return True
        return False

    # --- Audit Log Operations ---

    def log_audit(
        self,
        username: str,
        role: str,
        action: str,
        resource_id: Optional[str],
        status: str,
        reason: str,
        ip_address: str = "127.0.0.1"
    ) -> AuditLog:
        entry = AuditLog(
            id=str(uuid.uuid4())[:8].upper(),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            username=username,
            role=role,
            action=action,
            resource_id=resource_id,
            status=status,
            reason=reason,
            ip_address=ip_address
        )
        self.audit_logs.append(entry)
        return entry

    def list_audit_logs(self, limit: int = 100, status_filter: Optional[str] = None) -> List[AuditLog]:
        logs = self.audit_logs
        if status_filter:
            logs = [l for l in logs if l.status.upper() == status_filter.upper()]
        return list(reversed(logs[-limit:]))
