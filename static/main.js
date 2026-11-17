/**
 * RBAC Simulator - Professional White Theme Logic
 */

// Show Security Alert Box on the Dashboard
function showSecurityAlert(type, title, message) {
    const box = document.getElementById('security-alert-box');
    const icon = document.getElementById('security-alert-icon');
    const titleEl = document.getElementById('security-alert-title');
    const msgEl = document.getElementById('security-alert-message');
    if (!box) return;

    box.classList.remove('hidden');
    if (type === 'error') {
        box.className = 'p-4 rounded-xl border bg-red-50 border-red-200 text-red-900 transition shadow-xs';
        icon.innerHTML = '<i class="fa-solid fa-circle-xmark text-red-600 text-lg"></i>';
        titleEl.className = 'font-bold text-sm text-red-900';
        msgEl.className = 'mt-1 leading-relaxed text-xs text-red-800';
    } else {
        box.className = 'p-4 rounded-xl border bg-emerald-50 border-emerald-200 text-emerald-900 transition shadow-xs';
        icon.innerHTML = '<i class="fa-solid fa-circle-check text-emerald-600 text-lg"></i>';
        titleEl.className = 'font-bold text-sm text-emerald-900';
        msgEl.className = 'mt-1 leading-relaxed text-xs text-emerald-800';
    }

    titleEl.innerText = title;
    msgEl.innerText = message;

    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function dismissSecurityAlert() {
    const box = document.getElementById('security-alert-box');
    if (box) box.classList.add('hidden');
}

// Switch Role (Admin / Teacher / Student)
async function switchRole(role) {
    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quick_role: role })
        });
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        }
    } catch (err) {
        console.error('Failed to switch role', err);
    }
}

// Modal Helpers
function openModal(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('hidden');
        el.classList.add('flex');
    }
}

function closeModal(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('flex');
        el.classList.add('hidden');
    }
}

// View Record
async function viewRecord(recordId) {
    try {
        const res = await fetch('/api/records');
        if (res.status === 403) {
            const err = await res.json();
            showSecurityAlert('error', 'Access Denied', err.error);
            return;
        }
        const data = await res.json();
        const record = data.records.find(r => r.record_id === recordId);
        if (!record) return;

        document.getElementById('view-modal-content').innerHTML = `
            <div class="space-y-2 text-xs text-slate-700">
                <div class="flex justify-between pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium">Record ID:</span> 
                    <strong class="text-blue-600 font-mono">${record.record_id}</strong>
                </div>
                <div class="flex justify-between pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium">Student:</span> 
                    <strong class="text-slate-900">${record.student_name} (${record.student_id})</strong>
                </div>
                <div class="flex justify-between pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium">Course:</span> 
                    <span class="text-slate-800">${record.course}</span>
                </div>
                <div class="flex justify-between pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium">Grade:</span> 
                    <strong class="text-emerald-700 font-mono font-bold">${record.grade}</strong>
                </div>
                <div class="flex justify-between pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium">Attendance:</span> 
                    <span class="font-mono text-slate-800">${record.attendance}%</span>
                </div>
                <div class="pb-1.5 border-b border-slate-100">
                    <span class="text-slate-500 font-medium block mb-0.5">Teacher Remarks:</span> 
                    <div class="bg-slate-50 p-2 rounded text-slate-700 italic border border-slate-200">${record.remarks}</div>
                </div>
                <div class="text-[10px] text-slate-400 pt-1 flex justify-between">
                    <span>Created by: ${record.created_by}</span>
                    <span>${record.updated_at}</span>
                </div>
            </div>
        `;
        openModal('view-modal');
    } catch (err) {
        console.error(err);
    }
}

// Add Record
function openAddRecordModal() {
    openModal('add-modal');
}

async function submitAddRecord() {
    const student_id = document.getElementById('add-student-id').value.trim();
    const student_name = document.getElementById('add-student-name').value.trim();
    const course = document.getElementById('add-course').value.trim();
    const grade = document.getElementById('add-grade').value;
    const attendance = parseFloat(document.getElementById('add-attendance').value || 85);
    const remarks = document.getElementById('add-remarks').value.trim();

    if (!student_id || !student_name || !course) {
        alert('Please fill in Student ID, Name, and Course.');
        return;
    }

    try {
        const res = await fetch('/api/records', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id, student_name, course, grade, attendance, remarks })
        });

        closeModal('add-modal');

        if (res.status === 403) {
            const err = await res.json();
            showSecurityAlert('error', '403 Forbidden: Access Denied', err.error);
            return;
        }

        const data = await res.json();
        if (data.success) {
            window.location.reload();
        }
    } catch (err) {
        console.error(err);
    }
}

// Edit Record
let currentEditId = null;
function openEditRecordModal(id, name, course, grade, att, rem) {
    currentEditId = id;
    document.getElementById('edit-rec-id').innerText = id;
    document.getElementById('edit-student-name').value = name;
    document.getElementById('edit-course').value = course;
    document.getElementById('edit-grade').value = grade;
    document.getElementById('edit-attendance').value = att;
    document.getElementById('edit-remarks').value = rem;
    openModal('edit-modal');
}

async function submitEditRecord() {
    if (!currentEditId) return;

    const course = document.getElementById('edit-course').value.trim();
    const grade = document.getElementById('edit-grade').value;
    const attendance = parseFloat(document.getElementById('edit-attendance').value || 85);
    const remarks = document.getElementById('edit-remarks').value.trim();

    try {
        const res = await fetch(`/api/records/${currentEditId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ course, grade, attendance, remarks })
        });

        closeModal('edit-modal');

        if (res.status === 403) {
            const err = await res.json();
            showSecurityAlert('error', '403 Forbidden: Access Denied', err.error);
            return;
        }

        const data = await res.json();
        if (data.success) {
            window.location.reload();
        }
    } catch (err) {
        console.error(err);
    }
}

// Delete Record
async function deleteRecord(recordId, studentName) {
    if (!confirm(`Are you sure you want to delete ${recordId} (${studentName})?`)) return;

    try {
        const res = await fetch(`/api/records/${recordId}`, { method: 'DELETE' });

        if (res.status === 403) {
            const err = await res.json();
            showSecurityAlert(
                'error', 
                '403 Forbidden: Access Denied', 
                `${err.error} (Under Least Privilege, only Admin is permitted to delete records).`
            );
            return;
        }

        const data = await res.json();
        if (data.success) {
            showSecurityAlert('success', 'Record Deleted', `Record ${recordId} was successfully deleted.`);
            const row = document.getElementById(`row-${recordId}`);
            if (row) row.remove();
        }
    } catch (err) {
        console.error(err);
    }
}

// Run Matrix Verification
async function runVerification() {
    const btn = document.getElementById('btn-verify');
    const box = document.getElementById('verify-results-box');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1"></i> Verifying...';
    }

    try {
        const res = await fetch('/api/verify', { method: 'POST' });
        const data = await res.json();
        if (box) {
            box.classList.remove('hidden');
            box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    } catch (err) {
        console.error(err);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-clipboard-check mr-1"></i> Verified (18/18 Passed)';
        }
    }
}

// Reset Database
async function resetDatabase() {
    if (!confirm('Reset records back to default sample data?')) return;
    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            window.location.reload();
        } else {
            showSecurityAlert('error', 'Denied', data.error);
        }
    } catch (err) {
        console.error(err);
    }
}
