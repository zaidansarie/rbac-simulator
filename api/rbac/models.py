"""
Role-Based Access Control (RBAC) Simulator - Data Models
Defines Roles, Permissions, Users, Academic Records, and Audit Log structures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class Role(str, Enum):
    ADMIN = "Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"

    @classmethod
    def from_string(cls, value: str) -> "Role":
        for role in cls:
            if role.value.lower() == value.lower():
                return role
        raise ValueError(f"Unknown role: {value}")


class Permission(str, Enum):
    VIEW_RECORD = "record:view"
    ADD_RECORD = "record:add"
    EDIT_RECORD = "record:edit"
    DELETE_RECORD = "record:delete"
    VIEW_AUDIT_LOGS = "audit:view"
    MANAGE_USERS = "user:manage"


@dataclass
class User:
    username: str
    full_name: str
    role: Role
    password_hash: str
    salt: str
    student_id: Optional[str] = None
    is_active: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role.value,
            "student_id": self.student_id,
            "is_active": self.is_active,
            "is_locked": self.is_locked()
        }

    def is_locked(self) -> bool:
        if self.locked_until and datetime.now() < self.locked_until:
            return True
        return False


@dataclass
class AcademicRecord:
    record_id: str
    student_id: str
    student_name: str
    course: str
    grade: str
    attendance: float
    remarks: str
    created_by: str
    last_modified_by: str
    updated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "student_id": self.student_id,
            "student_name": self.student_name,
            "course": self.course,
            "grade": self.grade,
            "attendance": self.attendance,
            "remarks": self.remarks,
            "created_by": self.created_by,
            "last_modified_by": self.last_modified_by,
            "updated_at": self.updated_at
        }


@dataclass
class AuditLog:
    id: str
    timestamp: str
    username: str
    role: str
    action: str
    resource_id: Optional[str]
    status: str  # "ALLOWED" or "DENIED"
    reason: str
    ip_address: str = "127.0.0.1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "username": self.username,
            "role": self.role,
            "action": self.action,
            "resource_id": self.resource_id,
            "status": self.status,
            "reason": self.reason,
            "ip_address": self.ip_address
        }


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    role: str
    action: str
    resource_id: Optional[str] = None
