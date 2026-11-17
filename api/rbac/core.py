"""
Role-Based Access Control (RBAC) Simulator - Core Engine
Handles permission matrix definitions, Policy Decision Point (PDP),
Policy Enforcement Point (PEP), and least privilege validation.
"""

from typing import Dict, Set, List, Optional, Tuple, Any
from datetime import datetime
from rbac.models import Role, Permission, User, AccessDecision


class AccessDeniedError(Exception):
    """Raised when an authorization check fails (Access Denied)."""
    def __init__(self, message: str, role: str, action: str, resource_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.role = role
        self.action = action
        self.resource_id = resource_id
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class RBACEngine:
    """
    Core RBAC Policy Engine.
    Maintains the Role-to-Permission mapping and performs authorization decisions.
    """

    # Ground Truth Permissions Mapping (Defined per Activity 4 specification)
    DEFAULT_ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
        Role.ADMIN: {
            Permission.VIEW_RECORD,
            Permission.ADD_RECORD,
            Permission.EDIT_RECORD,
            Permission.DELETE_RECORD,
            Permission.VIEW_AUDIT_LOGS,
            Permission.MANAGE_USERS,
        },
        Role.TEACHER: {
            Permission.VIEW_RECORD,
            Permission.ADD_RECORD,
            Permission.EDIT_RECORD,
            # Note: Cannot DELETE records or manage users (Principle of Least Privilege)
        },
        Role.STUDENT: {
            Permission.VIEW_RECORD,
            # Note: Read-only access. Cannot ADD, EDIT, or DELETE records (Principle of Least Privilege)
        },
    }

    # Standard 4 CRUD Actions emphasized in PBL Activity 4
    CRUD_ACTIONS = [
        ("View Record", Permission.VIEW_RECORD),
        ("Add Record", Permission.ADD_RECORD),
        ("Edit Record", Permission.EDIT_RECORD),
        ("Delete Record", Permission.DELETE_RECORD),
    ]

    def __init__(self, role_permissions: Optional[Dict[Role, Set[Permission]]] = None):
        self.role_permissions = role_permissions or {
            role: set(perms) for role, perms in self.DEFAULT_ROLE_PERMISSIONS.items()
        }

    def get_permissions_for_role(self, role: Role) -> Set[Permission]:
        """Returns the set of permissions assigned to a specific role."""
        return self.role_permissions.get(role, set())

    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Checks if a role has the given permission."""
        return permission in self.get_permissions_for_role(role)

    def evaluate(
        self,
        user: Optional[User],
        permission: Permission,
        resource_id: Optional[str] = None,
        resource_owner_id: Optional[str] = None,
        strict_student_ownership: bool = False
    ) -> AccessDecision:
        """
        Policy Decision Point (PDP): Evaluates an access request.
        
        Args:
            user: The authenticated subject requesting access.
            permission: The permission (action) requested.
            resource_id: Optional identifier of the record.
            resource_owner_id: Optional student_id owning the record.
            strict_student_ownership: If True, students can only view records matching their student_id.
            
        Returns:
            AccessDecision detailing whether access is granted or denied and the reason.
        """
        if not user:
            return AccessDecision(
                allowed=False,
                reason="Authentication required: No authenticated user session found.",
                role="Unauthenticated",
                action=permission.value,
                resource_id=resource_id
            )

        if not user.is_active:
            return AccessDecision(
                allowed=False,
                reason=f"Account disabled: User '{user.username}' is marked inactive.",
                role=user.role.value,
                action=permission.value,
                resource_id=resource_id
            )

        if user.is_locked():
            return AccessDecision(
                allowed=False,
                reason=f"Account locked: User '{user.username}' is locked due to security policy.",
                role=user.role.value,
                action=permission.value,
                resource_id=resource_id
            )

        # 1. Base RBAC Check: Does the assigned role have this permission?
        role_allowed = self.has_permission(user.role, permission)
        if not role_allowed:
            return AccessDecision(
                allowed=False,
                reason=(
                    f"Access Denied: Role '{user.role.value}' does not hold the '{permission.value}' permission. "
                    f"Least Privilege principle strictly prohibits unauthorized modification/access."
                ),
                role=user.role.value,
                action=permission.value,
                resource_id=resource_id
            )

        # 2. Context-Aware Policy (Optional fine-grained check for student own record)
        if strict_student_ownership and user.role == Role.STUDENT and resource_owner_id:
            if user.student_id != resource_owner_id:
                return AccessDecision(
                    allowed=False,
                    reason=(
                        f"Access Denied: Student '{user.username}' (ID: {user.student_id}) "
                        f"is not permitted to view records belonging to student '{resource_owner_id}'."
                    ),
                    role=user.role.value,
                    action=permission.value,
                    resource_id=resource_id
                )

        return AccessDecision(
            allowed=True,
            reason=f"Access Granted: Role '{user.role.value}' is authorized to execute '{permission.value}'.",
            role=user.role.value,
            action=permission.value,
            resource_id=resource_id
        )

    def enforce(
        self,
        user: Optional[User],
        permission: Permission,
        resource_id: Optional[str] = None,
        resource_owner_id: Optional[str] = None,
        strict_student_ownership: bool = False
    ) -> AccessDecision:
        """
        Policy Enforcement Point (PEP): Enforces authorization and raises AccessDeniedError on denial.
        """
        decision = self.evaluate(
            user=user,
            permission=permission,
            resource_id=resource_id,
            resource_owner_id=resource_owner_id,
            strict_student_ownership=strict_student_ownership
        )
        if not decision.allowed:
            raise AccessDeniedError(
                message=decision.reason,
                role=decision.role,
                action=decision.action,
                resource_id=decision.resource_id
            )
        return decision

    def get_matrix_data(self) -> Dict[str, Any]:
        """
        Returns a structured matrix of Roles vs Permissions for UI & Verification.
        """
        roles = [Role.ADMIN, Role.TEACHER, Role.STUDENT]
        actions = [
            ("View Record", Permission.VIEW_RECORD, "View academic performance and attendance records"),
            ("Add Record", Permission.ADD_RECORD, "Create a new student academic record"),
            ("Edit Record", Permission.EDIT_RECORD, "Modify existing record grades, remarks, or attendance"),
            ("Delete Record", Permission.DELETE_RECORD, "Permanently delete an academic record"),
            ("View Audit Logs", Permission.VIEW_AUDIT_LOGS, "Inspect system-wide security audit and authorization logs"),
            ("Manage Users", Permission.MANAGE_USERS, "Create, disable, or adjust user accounts and roles"),
        ]

        matrix = {}
        for role in roles:
            matrix[role.value] = {}
            for label, perm, _ in actions:
                matrix[role.value][perm.value] = self.has_permission(role, perm)

        return {
            "roles": [r.value for r in roles],
            "actions": [{"label": label, "permission": perm.value, "description": desc} for label, perm, desc in actions],
            "matrix": matrix
        }
