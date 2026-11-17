# Role-Based Access Control (RBAC) Simulator

> **PBL Activity 4: Cryptography & Access Control**  
> **Syllabus Topic:** Authentication and Access Control  
> **Core Concepts Demonstrated:** Role-Based Access Control (RBAC), Principle of Least Privilege, Policy Enforcement Point (PEP) & Policy Decision Point (PDP), Salted SHA-256 Authentication vs. Authorization.

---

## 1. Project Overview

This project implements a complete **Role-Based Access Control (RBAC) Simulator** based on the specifications of **PBL Activity 4**. The simulator manages a repository of student academic records (grades, courses, attendance, and remarks) and enforces strict access control policies across three distinct user roles:

1. **Admin**: Has full administrative privileges (View, Add, Edit, and Delete records, plus view system audit logs and manage user accounts).
2. **Teacher**: Has privileges to View, Add, and Edit records (e.g., inputting student scores and attendance), but is **strictly forbidden from Deleting records** or viewing administrative audit logs under the **Principle of Least Privilege**.
3. **Student**: Has **Read-Only** privileges to View records. Barred from Adding, Editing, or Deleting records.

---

## 2. Key Security Concepts Implemented

### A. Distinction Between Authentication (AuthN) and Authorization (AuthZ)
* **Authentication ("Who are you?"):**
  * Handled via `rbac/auth.py`.
  * Passwords are never stored in plaintext; they are hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and a cryptographically secure 16-byte random salt (`secrets.token_hex(16)`).
  * Implements account lockout protection (locks account after 3 consecutive failed attempts).
  * Returns `401 Unauthorized` if identity cannot be verified.
* **Authorization / RBAC ("What are you permitted to do?"):**
  * Handled via `rbac/core.py`.
  * The Policy Enforcement Point (PEP) queries the Policy Decision Point (PDP) before allowing any CRUD operation on academic records.
  * Returns `403 Forbidden` (`AccessDeniedError`) with educational feedback explaining why the role is disallowed.

### B. Principle of Least Privilege (PoLP)
Every subject is granted only the minimum necessary set of privileges required for legitimate academic duties:
* Teachers require write access to record grades, but granting them deletion privileges would create unnecessary risk of permanent record loss.
* Students require visibility into academic performance, but granting them write access would allow unauthorized grade tampering.

### C. Security Audit Ledger
Every single authorization attempt (both `ALLOWED` and `DENIED`) is recorded into a security audit ledger with timestamp, username, role, action, target resource, outcome, and policy reason.

---

## 3. Ground-Truth Permissions Matrix

The simulator strictly enforces the following matrix defined in `verify_rbac.py` and `rbac/core.py`:

| Role | View Record (`record:view`) | Add Record (`record:add`) | Edit Record (`record:edit`) | Delete Record (`record:delete`) | View Audit Logs (`audit:view`) | Manage Users (`user:manage`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Admin** | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> |
| **Teacher** | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:green">**ALLOW**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> |
| **Student** | <span style="color:green">**ALLOW**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> | <span style="color:red">**DENY**</span> |

---

## 4. Pre-Configured Demo Accounts

| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `AdminPassword123!` | Aarav Sharma (System Admin - Full CRUD) |
| **Teacher** | `prof_sharma` | `TeacherPass123!` | Prof. Rajesh Sharma (View/Add/Edit) |
| **Teacher** | `dr_priya` | `TeacherPass123!` | Dr. Priya Patel (View/Add/Edit) |
| **Student** | `student_rohit` | `StudentPass123!` | Rohit Verma (Read-Only) |
| **Student** | `student_neha` | `StudentPass123!` | Neha Kulkarni (Read-Only) |
| **Student** | `student_ananya` | `StudentPass123!` | Ananya Iyer (Read-Only) |

---

## 5. How to Run the Project

You can run the simulator in multiple ways:

### Option 1: Master Launcher (Recommended)
```bash
python run.py
```
This presents an interactive menu allowing you to launch the Web UI, Terminal CLI, or Verification tests.

Alternatively, pass direct arguments:
```bash
python run.py web       # Launch Web Dashboard
python run.py cli       # Launch Terminal Simulator
python run.py verify    # Run Matrix Verification
python run.py test      # Run Automated Unit Tests
```

---

### Option 2: Modern Web Dashboard
Start the Flask web server:
```bash
python app.py
```
Then open your web browser at:
```
http://127.0.0.1:5000
```

#### Web Dashboard Highlights:
* **One-Click Role Switcher:** Switch between Admin, Teacher, and Student with one click to observe real-time permission changes.
* **Academic Records Table:** Try viewing, adding, editing, or deleting records under different roles. When a Teacher attempts to delete or a Student attempts to edit, an instant **403 Forbidden Access Denied** modal explains the policy violation.
* **Interactive Permissions Matrix:** View the complete matrix and test custom queries in the PDP sandbox.
* **Security Audit Log:** Inspect live authorization events (Admin-restricted).
* **Independent Matrix Verification Tab:** Run all 18 test cases with one click and see live PASS/FAIL badges.

---

### Option 3: Interactive Terminal CLI
For a pure console experience:
```bash
python cli.py
```
Features full interactive menus, color-coded status messages, user switching, and real-time CRUD operations.

---

### Option 4: Independent Matrix Verification
To execute the mandatory independent verification suite comparing the ground-truth matrix against actual runtime enforcement:
```bash
python verify_rbac.py
```
**Sample Output:**
```
================================================================================
 ROLE-BASED ACCESS CONTROL (RBAC) - INDEPENDENT VERIFICATION REPORT 
 Activity 4: Verification of Permissions Matrix against Allowed & Denied Actions
================================================================================
Role       | Action Name                  | Expected | Actual   | Status
--------------------------------------------------------------------------------
Admin      | View Record (Read)           | ALLOW    | ALLOWED  | [ PASS ]
Admin      | Add Record (Create)          | ALLOW    | ALLOWED  | [ PASS ]
Admin      | Edit Record (Update)         | ALLOW    | ALLOWED  | [ PASS ]
Admin      | Delete Record (Delete)       | ALLOW    | ALLOWED  | [ PASS ]
Admin      | View Audit Logs (Admin)      | ALLOW    | ALLOWED  | [ PASS ]
Admin      | Manage Users (Admin)         | ALLOW    | ALLOWED  | [ PASS ]
Teacher    | View Record (Read)           | ALLOW    | ALLOWED  | [ PASS ]
Teacher    | Add Record (Create)          | ALLOW    | ALLOWED  | [ PASS ]
Teacher    | Edit Record (Update)         | ALLOW    | ALLOWED  | [ PASS ]
Teacher    | Delete Record (Delete)       | DENY     | DENIED   | [ PASS ]
Teacher    | View Audit Logs (Admin)      | DENY     | DENIED   | [ PASS ]
Teacher    | Manage Users (Admin)         | DENY     | DENIED   | [ PASS ]
Student    | View Record (Read)           | ALLOW    | ALLOWED  | [ PASS ]
Student    | Add Record (Create)          | DENY     | DENIED   | [ PASS ]
Student    | Edit Record (Update)         | DENY     | DENIED   | [ PASS ]
Student    | Delete Record (Delete)       | DENY     | DENIED   | [ PASS ]
Student    | View Audit Logs (Admin)      | DENY     | DENIED   | [ PASS ]
Student    | Manage Users (Admin)         | DENY     | DENIED   | [ PASS ]
--------------------------------------------------------------------------------
Total Tests Run: 18
Passed:          18
Failed:          0
Success Rate:    100.0%

 VERIFICATION PASSED: Every role strictly obeys the least privilege matrix!
================================================================================
```

---

### Option 5: Automated Unit Test Suite
To run the automated `unittest` test suite covering password hashing, lockout logic, PEP/PDP decisions, and audit logging:
```bash
python -m unittest discover tests
```

---

## 6. Project Architecture

```
Cryptography PBL/
├── rbac/
│   ├── __init__.py         # Package initialization
│   ├── auth.py             # Salted SHA-256 hashing, session & lockout management
│   ├── models.py           # Role, Permission, User, AcademicRecord, AuditLog models
│   ├── core.py             # RBAC Policy Engine, PDP and PEP enforcement
│   └── database.py         # In-memory database with pre-seeded users and records
├── templates/
│   ├── base.html           # Base layout with navigation and role switcher
│   ├── index.html          # Main dashboard & Academic Records CRUD management
│   ├── matrix.html         # Ground-truth permissions matrix & interactive PDP evaluator
│   ├── audit.html          # Security audit ledger (restricted to Admin)
│   └── verify.html         # Verification runner and visual report
├── static/
│   ├── style.css           # Custom styling and animations
│   └── main.js             # Client-side API integration and policy enforcement alerts
├── tests/
│   ├── __init__.py
│   └── test_rbac.py        # Automated unit tests
├── cli.py                  # Interactive terminal interface
├── app.py                  # Flask web application server
├── verify_rbac.py          # Independent verification script (Activity 4 requirement)
├── run.py                  # Master launcher for Web, CLI, or Tests
├── requirements.txt        # Python dependencies
└── README.md               # Documentation
```
