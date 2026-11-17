"""
Role-Based Access Control (RBAC) Simulator - Interactive CLI
Provides an interactive terminal simulation to test Roles (Admin, Teacher, Student),
CRUD operations on academic records, permission matrix evaluation, and security audit logs.
"""

import sys
import getpass
from typing import Optional
from rbac.models import Role, Permission, User
from rbac.core import RBACEngine, AccessDeniedError
from rbac.auth import AuthenticationService
from rbac.database import Database
from verify_rbac import PermissionsMatrixVerifier


# ANSI Color formatting
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"


class RBACSimulatorCLI:
    def __init__(self):
        self.db = Database()
        self.auth = AuthenticationService()
        self.engine = RBACEngine()
        self.current_user: Optional[User] = None
        self.session_token: Optional[str] = None

    def print_header(self):
        print(f"\n{Color.CYAN}{Color.BOLD}" + "=" * 76)
        print("          ROLE-BASED ACCESS CONTROL (RBAC) SIMULATOR - PBL ACTIVITY 4")
        print("          Topics: Authentication, Authorization & Least Privilege")
        print("=" * 76 + f"{Color.RESET}")

    def print_user_banner(self):
        if self.current_user:
            role_color = {
                Role.ADMIN: Color.RED,
                Role.TEACHER: Color.YELLOW,
                Role.STUDENT: Color.GREEN,
            }.get(self.current_user.role, Color.CYAN)

            print(f"\n{Color.BOLD}Current Session:{Color.RESET} "
                  f"User: {Color.CYAN}{self.current_user.full_name} ({self.current_user.username}){Color.RESET} | "
                  f"Role: {role_color}[{self.current_user.role.value}]{Color.RESET}")
            perms = [p.value for p in self.engine.get_permissions_for_role(self.current_user.role)]
            print(f"{Color.BOLD}Assigned Permissions:{Color.RESET} {', '.join(perms)}")
        else:
            print(f"\n{Color.YELLOW}[No active session. Please log in]{Color.RESET}")

    def login_menu(self):
        while not self.current_user:
            self.print_header()
            print("\nSelect an action to begin:")
            print("1. Quick Login as Admin (admin)")
            print("2. Quick Login as Teacher (prof_sharma)")
            print("3. Quick Login as Student (student_rohit)")
            print("4. Manual Login (Enter username & password)")
            print("5. Run Independent Verification Matrix")
            print("6. Exit")

            choice = input(f"\n{Color.BOLD}Enter choice (1-6): {Color.RESET}").strip()

            if choice == "1":
                self._do_login("admin", self.db.DEFAULT_PASSWORDS["admin"])
            elif choice == "2":
                self._do_login("prof_sharma", self.db.DEFAULT_PASSWORDS["prof_sharma"])
            elif choice == "3":
                self._do_login("student_rohit", self.db.DEFAULT_PASSWORDS["student_rohit"])
            elif choice == "4":
                u = input("Username: ").strip()
                p = input("Password: ").strip()
                self._do_login(u, p)
            elif choice == "5":
                verifier = PermissionsMatrixVerifier()
                verifier.run_all_tests(verbose=True)
                input(f"{Color.CYAN}Press Enter to return to login menu...{Color.RESET}")
            elif choice == "6":
                print("\nExiting RBAC Simulator. Goodbye!")
                sys.exit(0)
            else:
                print(f"{Color.RED}Invalid choice. Please select 1-6.{Color.RESET}")

    def _do_login(self, username: str, password: str):
        success, msg, token, user = self.auth.authenticate(username, password, self.db.users)
        if success:
            self.current_user = user
            self.session_token = token
            self.db.log_audit(
                username=user.username,
                role=user.role.value,
                action="auth:login",
                resource_id=None,
                status="ALLOWED",
                reason=msg
            )
            print(f"\n{Color.GREEN}{msg}{Color.RESET}")
        else:
            if user:
                self.db.log_audit(
                    username=username,
                    role=user.role.value if user else "Unknown",
                    action="auth:login",
                    resource_id=None,
                    status="DENIED",
                    reason=msg
                )
            print(f"\n{Color.RED}{msg}{Color.RESET}")

    def main_menu(self):
        while self.current_user:
            self.print_user_banner()
            print("\n" + "-" * 40)
            print("1. View All Academic Records (record:view)")
            print("2. Add New Academic Record   (record:add)")
            print("3. Edit Academic Record      (record:edit)")
            print("4. Delete Academic Record    (record:delete)")
            print("5. View Permissions Matrix   (Full Matrix)")
            print("6. View Security Audit Logs  (audit:view)")
            print("7. Run Independent Matrix Verification")
            print("8. Switch User / Role")
            print("9. Explain AuthN vs AuthZ Concepts")
            print("0. Log Out & Exit")
            print("-" * 40)

            choice = input(f"{Color.BOLD}Select operation (0-9): {Color.RESET}").strip()

            if choice == "1":
                self.handle_view_records()
            elif choice == "2":
                self.handle_add_record()
            elif choice == "3":
                self.handle_edit_record()
            elif choice == "4":
                self.handle_delete_record()
            elif choice == "5":
                self.handle_view_matrix()
            elif choice == "6":
                self.handle_view_audit_logs()
            elif choice == "7":
                verifier = PermissionsMatrixVerifier()
                verifier.run_all_tests(verbose=True)
            elif choice == "8":
                self.current_user = None
                self.session_token = None
                self.login_menu()
            elif choice == "9":
                self.handle_explain_concepts()
            elif choice == "0":
                print(f"\n{Color.YELLOW}Logged out successfully. Goodbye!{Color.RESET}")
                sys.exit(0)
            else:
                print(f"{Color.RED}Invalid option.{Color.RESET}")

    # --- Operation Handlers with PEP Enforcement ---

    def handle_view_records(self):
        """Attempts to view records under PEP enforcement."""
        try:
            self.engine.enforce(self.current_user, Permission.VIEW_RECORD)
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.VIEW_RECORD.value,
                resource_id="ALL",
                status="ALLOWED",
                reason="Viewed academic records list"
            )
            records = self.db.list_records()
            print(f"\n{Color.BOLD}{'ID':<9} | {'Student ID':<10} | {'Student Name':<16} | {'Grade':<6} | {'Att %':<6} | {'Course'}{Color.RESET}")
            print("-" * 80)
            for r in records:
                print(f"{r.record_id:<9} | {r.student_id:<10} | {r.student_name:<16} | {r.grade:<6} | {r.attendance:<6.1f} | {r.course}")
            print("-" * 80)
        except AccessDeniedError as e:
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.VIEW_RECORD.value,
                resource_id="ALL",
                status="DENIED",
                reason=e.message
            )
            print(f"\n{Color.RED}[SECURITY ALERT] ACCESS DENIED: {e.message}{Color.RESET}")

    def handle_add_record(self):
        """Attempts to add a record under PEP enforcement."""
        try:
            self.engine.enforce(self.current_user, Permission.ADD_RECORD)
            print(f"\n{Color.GREEN}[ACCESS GRANTED] Role '{self.current_user.role.value}' is authorized to add records.{Color.RESET}")
            s_id = input("Student ID (e.g. STU-1006): ").strip()
            name = input("Student Name: ").strip()
            course = input("Course Name: ").strip()
            grade = input("Grade (e.g. A, B+, C): ").strip()
            att = float(input("Attendance Percentage (0-100): ").strip() or "85")
            rem = input("Teacher Remarks: ").strip()

            rec = self.db.create_record(
                student_id=s_id,
                student_name=name,
                course=course,
                grade=grade,
                attendance=att,
                remarks=rem,
                created_by=self.current_user.username
            )
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.ADD_RECORD.value,
                resource_id=rec.record_id,
                status="ALLOWED",
                reason=f"Created record {rec.record_id} for student {name}"
            )
            print(f"{Color.GREEN}Record {rec.record_id} successfully created!{Color.RESET}")
        except AccessDeniedError as e:
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.ADD_RECORD.value,
                resource_id=None,
                status="DENIED",
                reason=e.message
            )
            print(f"\n{Color.RED}[SECURITY ALERT] ACCESS DENIED!{Color.RESET}")
            print(f"{Color.RED}Reason: {e.message}{Color.RESET}")
            print(f"{Color.YELLOW}Note: Under Least Privilege, role '{self.current_user.role.value}' cannot create records.{Color.RESET}")
        except Exception as ex:
            print(f"{Color.RED}Input error: {ex}{Color.RESET}")

    def handle_edit_record(self):
        """Attempts to edit an existing record under PEP enforcement."""
        try:
            rec_id = input("\nEnter Record ID to edit (e.g., REC-101): ").strip().upper()
            self.engine.enforce(self.current_user, Permission.EDIT_RECORD, resource_id=rec_id)
            rec = self.db.get_record(rec_id)
            if not rec:
                print(f"{Color.RED}Record {rec_id} not found.{Color.RESET}")
                return

            print(f"{Color.GREEN}[ACCESS GRANTED] Role '{self.current_user.role.value}' is authorized to edit records.{Color.RESET}")
            print(f"Editing {rec_id} for {rec.student_name} (Current Grade: {rec.grade}, Attendance: {rec.attendance}%)")
            new_grade = input(f"New Grade [{rec.grade}]: ").strip() or rec.grade
            new_att_str = input(f"New Attendance % [{rec.attendance}]: ").strip()
            new_att = float(new_att_str) if new_att_str else rec.attendance
            new_rem = input(f"New Remarks [{rec.remarks}]: ").strip() or rec.remarks

            self.db.update_record(
                record_id=rec_id,
                grade=new_grade,
                attendance=new_att,
                remarks=new_rem,
                modified_by=self.current_user.username
            )
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.EDIT_RECORD.value,
                resource_id=rec_id,
                status="ALLOWED",
                reason=f"Updated grade to {new_grade}, attendance to {new_att}%"
            )
            print(f"{Color.GREEN}Record {rec_id} successfully updated!{Color.RESET}")
        except AccessDeniedError as e:
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.EDIT_RECORD.value,
                resource_id=rec_id if 'rec_id' in locals() else None,
                status="DENIED",
                reason=e.message
            )
            print(f"\n{Color.RED}[SECURITY ALERT] ACCESS DENIED!{Color.RESET}")
            print(f"{Color.RED}Reason: {e.message}{Color.RESET}")
            print(f"{Color.YELLOW}Note: Students cannot modify records.{Color.RESET}")

    def handle_delete_record(self):
        """Attempts to delete a record under PEP enforcement."""
        try:
            rec_id = input("\nEnter Record ID to delete (e.g., REC-105): ").strip().upper()
            # Enforce DELETE_RECORD permission
            self.engine.enforce(self.current_user, Permission.DELETE_RECORD, resource_id=rec_id)
            rec = self.db.get_record(rec_id)
            if not rec:
                print(f"{Color.RED}Record {rec_id} not found.{Color.RESET}")
                return

            confirm = input(f"Confirm deletion of {rec_id} ({rec.student_name})? [y/N]: ").strip().lower()
            if confirm == "y":
                self.db.delete_record(rec_id)
                self.db.log_audit(
                    username=self.current_user.username,
                    role=self.current_user.role.value,
                    action=Permission.DELETE_RECORD.value,
                    resource_id=rec_id,
                    status="ALLOWED",
                    reason=f"Record {rec_id} permanently deleted by {self.current_user.username}"
                )
                print(f"{Color.GREEN}Record {rec_id} deleted successfully.{Color.RESET}")
            else:
                print("Deletion cancelled.")
        except AccessDeniedError as e:
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.DELETE_RECORD.value,
                resource_id=rec_id if 'rec_id' in locals() else None,
                status="DENIED",
                reason=e.message
            )
            print(f"\n{Color.RED}[SECURITY ALERT] ACCESS DENIED!{Color.RESET}")
            print(f"{Color.RED}Reason: {e.message}{Color.RESET}")
            print(f"{Color.YELLOW}Least Privilege Rule: Only Admin can delete records. "
                  f"Role '{self.current_user.role.value}' is strictly forbidden.{Color.RESET}")

    def handle_view_matrix(self):
        """Displays the full permissions matrix."""
        print("\n" + "=" * 70)
        print("          OFFICIAL RBAC PERMISSIONS MATRIX")
        print("=" * 70)
        matrix_data = self.engine.get_matrix_data()
        roles = matrix_data["roles"]
        actions = matrix_data["actions"]

        print(f"{'Action / Permission':<30} | " + " | ".join([f"{r:<10}" for r in roles]))
        print("-" * 70)
        for act in actions:
            row = [f"{act['label']:<30}"]
            for r in roles:
                allowed = matrix_data["matrix"][r].get(act["permission"], False)
                symbol = f"{Color.GREEN} ALLOW  {Color.RESET}" if allowed else f"{Color.RED}  DENY  {Color.RESET}"
                row.append(symbol)
            print(" | ".join(row))
        print("=" * 70)

    def handle_view_audit_logs(self):
        """Attempts to view security audit logs under PEP enforcement."""
        try:
            self.engine.enforce(self.current_user, Permission.VIEW_AUDIT_LOGS)
            logs = self.db.list_audit_logs(limit=15)
            print("\n" + "=" * 90)
            print("                     SECURITY AUDIT LOGS (ADMIN ONLY)")
            print("=" * 90)
            print(f"{'Timestamp':<19} | {'User':<14} | {'Role':<8} | {'Status':<8} | {'Action':<15} | {'Reason'}")
            print("-" * 90)
            for log in logs:
                st_color = Color.GREEN if log.status == "ALLOWED" else Color.RED
                print(f"{log.timestamp:<19} | {log.username:<14} | {log.role:<8} | {st_color}{log.status:<8}{Color.RESET} | {log.action:<15} | {log.reason[:30]}")
            print("=" * 90)
        except AccessDeniedError as e:
            self.db.log_audit(
                username=self.current_user.username,
                role=self.current_user.role.value,
                action=Permission.VIEW_AUDIT_LOGS.value,
                resource_id=None,
                status="DENIED",
                reason=e.message
            )
            print(f"\n{Color.RED}[SECURITY ALERT] ACCESS DENIED: {e.message}{Color.RESET}")

    def handle_explain_concepts(self):
        """Prints educational distinction between Authentication and Authorization."""
        comp = self.auth.get_auth_comparison()
        print("\n" + "=" * 76)
        print("     DISTINCTION BETWEEN AUTHENTICATION AND ACCESS CONTROL (AUTHORIZATION)")
        print("=" * 76)
        print(f"{Color.CYAN}{Color.BOLD}1. AUTHENTICATION (AuthN):{Color.RESET}")
        print(f"   - Question:       {comp['authentication']['question']}")
        print(f"   - Mechanism:      {comp['authentication']['mechanism']}")
        print(f"   - Standard Code:  {comp['authentication']['failure_code']}")
        print(f"   - Failure State:  {comp['authentication']['failure_meaning']}")
        print()
        print(f"{Color.MAGENTA}{Color.BOLD}2. AUTHORIZATION / RBAC (AuthZ):{Color.RESET}")
        print(f"   - Question:       {comp['authorization']['question']}")
        print(f"   - Mechanism:      {comp['authorization']['mechanism']}")
        print(f"   - Standard Code:  {comp['authorization']['failure_code']}")
        print(f"   - Failure State:  {comp['authorization']['failure_meaning']}")
        print()
        print(f"{Color.YELLOW}{Color.BOLD}3. PRINCIPLE OF LEAST PRIVILEGE:{Color.RESET}")
        print("   - Subjects (users) are granted only the minimum clearance necessary")
        print("     to execute their legitimate responsibilities.")
        print("   - In this simulator: Teacher can edit grades but cannot delete records;")
        print("     Student can view academic records but cannot edit or delete any.")
        print("=" * 76)


def main():
    cli = RBACSimulatorCLI()
    cli.login_menu()
    cli.main_menu()


if __name__ == "__main__":
    main()
