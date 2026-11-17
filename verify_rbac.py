"""
Role-Based Access Control (RBAC) Simulator - Independent Verification Suite
Implements the PBL Activity 4 requirement:
"Independent verification: Manually define a permissions matrix, then test each role against allowed and denied actions."
"""

import sys
from typing import Dict, List, Tuple, Any
from rbac.models import Role, Permission, User
from rbac.core import RBACEngine, AccessDeniedError
from rbac.database import Database


class PermissionsMatrixVerifier:
    """
    Independent Verification Engine.
    Manually specifies the expected ground-truth access control matrix
    and validates every role against allowed and denied actions.
    """

    # --- Manually Defined Ground-Truth Permissions Matrix ---
    # Expected outcome for each (Role, Action) tuple: True = ALLOW, False = DENY
    GROUND_TRUTH_MATRIX: Dict[Role, Dict[Permission, bool]] = {
        Role.ADMIN: {
            Permission.VIEW_RECORD: True,
            Permission.ADD_RECORD: True,
            Permission.EDIT_RECORD: True,
            Permission.DELETE_RECORD: True,
            Permission.VIEW_AUDIT_LOGS: True,
            Permission.MANAGE_USERS: True,
        },
        Role.TEACHER: {
            Permission.VIEW_RECORD: True,
            Permission.ADD_RECORD: True,
            Permission.EDIT_RECORD: True,
            Permission.DELETE_RECORD: False,   # Principle of Least Privilege: Teachers cannot delete records
            Permission.VIEW_AUDIT_LOGS: False, # Teachers cannot view system security logs
            Permission.MANAGE_USERS: False,    # Teachers cannot alter user accounts
        },
        Role.STUDENT: {
            Permission.VIEW_RECORD: True,      # Read-only access to academic records
            Permission.ADD_RECORD: False,      # Students cannot create records
            Permission.EDIT_RECORD: False,     # Students cannot alter grades/attendance
            Permission.DELETE_RECORD: False,   # Students cannot delete records
            Permission.VIEW_AUDIT_LOGS: False, # Students cannot view security audit logs
            Permission.MANAGE_USERS: False,    # Students cannot manage user accounts
        },
    }

    ACTION_NAMES = {
        Permission.VIEW_RECORD: "View Record (Read)",
        Permission.ADD_RECORD: "Add Record (Create)",
        Permission.EDIT_RECORD: "Edit Record (Update)",
        Permission.DELETE_RECORD: "Delete Record (Delete)",
        Permission.VIEW_AUDIT_LOGS: "View Audit Logs (Admin)",
        Permission.MANAGE_USERS: "Manage Users (Admin)",
    }

    def __init__(self):
        self.db = Database()
        self.engine = RBACEngine()

    def run_all_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Executes exhaustive verification across all Roles and Actions.
        Returns a structured dictionary of results and statistics.
        """
        results: List[Dict[str, Any]] = []
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        # Create temporary dummy subjects for each role
        subjects = {
            Role.ADMIN: self.db.users["admin"],
            Role.TEACHER: self.db.users["prof_sharma"],
            Role.STUDENT: self.db.users["student_rohit"],
        }

        for role, user in subjects.items():
            for perm, expected_allow in self.GROUND_TRUTH_MATRIX[role].items():
                total_tests += 1
                action_name = self.ACTION_NAMES.get(perm, perm.value)
                test_passed = False
                actual_result = None
                error_msg = None

                # Test 1: Policy Decision Point evaluation
                decision = self.engine.evaluate(user=user, permission=perm, resource_id="REC-TEST")
                pdp_correct = (decision.allowed == expected_allow)

                # Test 2: Policy Enforcement Point execution
                pep_correct = False
                try:
                    self.engine.enforce(user=user, permission=perm, resource_id="REC-TEST")
                    # If no exception was raised, action was permitted
                    if expected_allow:
                        pep_correct = True
                        actual_result = "ALLOWED"
                    else:
                        pep_correct = False
                        actual_result = "UNAUTHORIZED_ALLOW (Security Violation)"
                except AccessDeniedError as e:
                    # If exception was raised, action was denied
                    if not expected_allow:
                        pep_correct = True
                        actual_result = "DENIED"
                        error_msg = e.message
                    else:
                        pep_correct = False
                        actual_result = "FALSE_DENIAL"
                        error_msg = e.message

                # Log to DB audit log
                self.db.log_audit(
                    username=user.username,
                    role=user.role.value,
                    action=perm.value,
                    resource_id="REC-TEST",
                    status="ALLOWED" if decision.allowed else "DENIED",
                    reason=f"[Verification Test] {decision.reason}",
                    ip_address="127.0.0.1"
                )

                test_passed = pdp_correct and pep_correct
                if test_passed:
                    passed_tests += 1
                else:
                    failed_tests += 1

                results.append({
                    "role": role.value,
                    "permission": perm.value,
                    "action_name": action_name,
                    "expected": "ALLOW" if expected_allow else "DENY",
                    "actual": actual_result,
                    "passed": test_passed,
                    "reason": decision.reason if test_passed else error_msg
                })

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate_percent": round((passed_tests / total_tests) * 100, 2) if total_tests > 0 else 0.0,
            "all_passed": (failed_tests == 0),
            "results": results
        }

        if verbose:
            self.print_verification_report(summary)

        return summary

    def print_verification_report(self, summary: Dict[str, Any]):
        """Prints a clean ASCII verification report to standard output."""
        print("\n" + "=" * 80)
        print(" ROLE-BASED ACCESS CONTROL (RBAC) - INDEPENDENT VERIFICATION REPORT ")
        print(" Activity 4: Verification of Permissions Matrix against Allowed & Denied Actions")
        print("=" * 80)
        print(f"{'Role':<10} | {'Action Name':<28} | {'Expected':<8} | {'Actual':<8} | {'Status':<6}")
        print("-" * 80)

        for item in summary["results"]:
            status_symbol = " PASS " if item["passed"] else "*FAIL*"
            print(
                f"{item['role']:<10} | "
                f"{item['action_name']:<28} | "
                f"{item['expected']:<8} | "
                f"{item['actual']:<8} | "
                f"[{status_symbol}]"
            )

        print("-" * 80)
        print(f"Total Tests Run: {summary['total_tests']}")
        print(f"Passed:          {summary['passed_tests']}")
        print(f"Failed:          {summary['failed_tests']}")
        print(f"Success Rate:    {summary['success_rate_percent']}%")
        if summary["all_passed"]:
            print("\n VERIFICATION PASSED: Every role strictly obeys the least privilege matrix!")
        else:
            print("\n VERIFICATION FAILED: Discrepancies detected between matrix and engine.")
        print("=" * 80 + "\n")


def main():
    verifier = PermissionsMatrixVerifier()
    summary = verifier.run_all_tests(verbose=True)
    if not summary["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
