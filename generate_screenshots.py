"""
Generate crisp, fully-styled, high-resolution screenshots of the RBAC Simulator for the PBL Report.
"""
import threading
import time
import os
from api.index import app
from playwright.sync_api import sync_playwright

def run_server():
    app.run(port=5030, debug=False, use_reloader=False)

def main():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)

    os.makedirs("screenshots", exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 820})
        
        # 1. Admin Dashboard
        print("Capturing 1: Admin Dashboard...")
        page.goto("http://127.0.0.1:5030/")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        page.screenshot(path="screenshots/01_admin_dashboard.png")

        # 2. Switch to Teacher
        print("Capturing 2: Teacher Dashboard...")
        page.click("#btn-role-Teacher")
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshots/02_teacher_dashboard.png")

        # 3. Switch to Student
        print("Capturing 3: Student Dashboard...")
        page.click("#btn-role-Student")
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshots/03_student_dashboard.png")

        # 4. Permissions Matrix
        print("Capturing 4: Permissions Matrix...")
        page.goto("http://127.0.0.1:5030/matrix")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        page.screenshot(path="screenshots/04_permissions_matrix.png")

        # 5. Switch to Admin & Audit Logs
        print("Capturing 5: Audit Logs...")
        page.goto("http://127.0.0.1:5030/")
        page.wait_for_load_state("networkidle")
        page.click("#btn-role-Admin")
        page.wait_for_timeout(800)
        page.goto("http://127.0.0.1:5030/audit")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        page.screenshot(path="screenshots/05_audit_logs.png")

        # 6. Verification Page
        print("Capturing 6: Verification Results...")
        page.goto("http://127.0.0.1:5030/verify")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="screenshots/06_matrix_verification.png")

        browser.close()

    print("All styled screenshots successfully captured in screenshots/ directory!")

if __name__ == "__main__":
    main()
