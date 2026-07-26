import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Plus, Shield, Trash2, UserCog, KeyRound, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { staffApi, departmentsApi, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { StaffMember, CreateStaffPayload, StaffAssignment } from '../lib/types';

export default function StaffManagement() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState<{ id: number; name: string; password: string } | null>(null);

  const staffQuery = useQuery({
    queryKey: ['staff'],
    queryFn: () => staffApi.list(),
  });

  const deptsQuery = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentsApi.list(),
  });

  const allDepts = useMemo(() => {
    const raw = deptsQuery.data;
    if (Array.isArray(raw)) return raw;
    if (raw && typeof raw === 'object') {
      const r = raw as { departments?: { name: string; label?: string }[] };
      return r.departments || [];
    }
    return [];
  }, [deptsQuery.data]);

  const staff: StaffMember[] = useMemo(() => {
    const raw = staffQuery.data as { staff?: StaffMember[] } | undefined;
    return raw?.staff || [];
  }, [staffQuery.data]);

  const canManageRole = currentUser?.role === 'admin';

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Staff Management</h1>
          <p className="text-sm text-slate-500">
            {staff.length} staff member{staff.length !== 1 ? 's' : ''} · {allDepts.length} departments
          </p>
        </div>
        <button type="button" className="btn-primary" onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4" />
          Add Staff
        </button>
      </div>

      {/* Staff table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border text-xs font-medium uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Departments</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {staff.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">
                    No staff members yet. Add one to get started.
                  </td>
                </tr>
              )}
              {staff.map((s) => (
                <StaffRow
                  key={s.id}
                  staff={s}
                  canManageRole={canManageRole}
                  onPasswordReset={(id, name) => {
                    staffApi.resetPassword(id).then((res) => {
                      setShowPasswordModal({ id, name, password: res.temporary_password });
                      queryClient.invalidateQueries({ queryKey: ['staff'] });
                    }).catch((err) => toast.error(err.message));
                  }}
                  onRemove={(id) => {
                    staffApi.remove(id).then(() => {
                      toast.success('Staff removed');
                      queryClient.invalidateQueries({ queryKey: ['staff'] });
                    }).catch((err) => toast.error(err.message));
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Staff Modal */}
      {showAddModal && (
        <AddStaffModal
          departments={allDepts.map((d: { name: string; label?: string }) => ({ name: d.name, label: d.label || d.name }))}
          canManageRole={canManageRole}
          onClose={() => setShowAddModal(false)}
          onCreated={(password) => {
            setShowAddModal(false);
            setShowPasswordModal({ id: 0, name: 'New Staff', password });
            queryClient.invalidateQueries({ queryKey: ['staff'] });
          }}
        />
      )}

      {/* Password Reveal Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="card relative w-full max-w-md p-6">
            <button type="button" className="btn-ghost absolute right-2 top-2 !px-2" onClick={() => setShowPasswordModal(null)}>
              <X className="h-5 w-5" />
            </button>
            <div className="text-center">
              <KeyRound className="mx-auto mb-3 h-10 w-10 text-brand" />
              <h2 className="text-base font-semibold text-slate-900">Temporary Password</h2>
              <p className="mt-1 text-sm text-slate-500">
                Share this with {showPasswordModal.name}. It will not be shown again.
              </p>
              <div className="mt-4 rounded-lg bg-slate-100 px-4 py-3 font-mono text-lg font-bold tracking-wider text-slate-900">
                {showPasswordModal.password}
              </div>
              <button
                type="button"
                className="btn-primary mt-4 w-full"
                onClick={() => {
                  navigator.clipboard.writeText(showPasswordModal.password)
                    .then(() => toast.success('Copied'))
                    .catch(() => toast.error('Copy failed'));
                }}
              >
                Copy Password
              </button>
              <button type="button" className="btn-secondary mt-2 w-full" onClick={() => setShowPasswordModal(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StaffRow({
  staff,
  canManageRole,
  onPasswordReset,
  onRemove,
}: {
  staff: StaffMember;
  canManageRole: boolean;
  onPasswordReset: (id: number, name: string) => void;
  onRemove: (id: number) => void;
}) {
  const roleBadge = (role: string) => {
    const styles: Record<string, string> = {
      admin: 'bg-purple-100 text-purple-700',
      hr_manager: 'bg-sky-100 text-sky-700',
      user: 'bg-slate-100 text-slate-700',
    };
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles[role] || styles.user}`}>
        {role === 'hr_manager' ? 'HR' : role === 'admin' ? 'Admin' : 'User'}
      </span>
    );
  };

  return (
    <tr className="border-b border-surface-border last:border-0 hover:bg-slate-50">
      <td className="px-4 py-3 font-medium text-slate-900">{staff.name}</td>
      <td className="px-4 py-3 text-slate-600">{staff.email}</td>
      <td className="px-4 py-3">{roleBadge(staff.role)}</td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {staff.assignments.map((a) => (
            <span key={a.department} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {a.department_name || a.department}{a.title ? ` — ${a.title}` : ''}
            </span>
          ))}
          {staff.assignments.length === 0 && <span className="text-xs text-slate-400">None</span>}
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1 text-xs ${staff.first_login ? 'text-amber-600' : 'text-emerald-600'}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${staff.first_login ? 'bg-amber-400' : 'bg-emerald-400'}`} />
          {staff.first_login ? 'Pending' : 'Active'}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="flex justify-end gap-1">
          <button
            type="button"
            className="btn-ghost !px-2 !py-1"
            title="Reset password"
            onClick={() => onPasswordReset(staff.id, staff.name)}
          >
            <KeyRound className="h-4 w-4" />
          </button>
          {canManageRole && (
            <button
              type="button"
              className="btn-ghost !px-2 !py-1 text-rose-500 hover:text-rose-700"
              title="Remove from all departments"
              onClick={() => {
                if (window.confirm(`Remove ${staff.name} from all departments?`)) {
                  onRemove(staff.id);
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

function AddStaffModal({
  departments,
  canManageRole,
  onClose,
  onCreated,
}: {
  departments: { name: string; label: string }[];
  canManageRole: boolean;
  onClose: () => void;
  onCreated: (tempPassword: string) => void;
}) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('user');
  const [assignments, setAssignments] = useState<{ department: string; title: string }[]>([]);
  const [saving, setSaving] = useState(false);

  const addAssignment = (dept: string) => {
    if (!assignments.find((a) => a.department === dept)) {
      setAssignments([...assignments, { department: dept, title: '' }]);
    }
  };

  const removeAssignment = (dept: string) => {
    setAssignments(assignments.filter((a) => a.department !== dept));
  };

  const handleSubmit = async () => {
    if (!email.trim() || !name.trim()) {
      toast.error('Email and name are required');
      return;
    }
    setSaving(true);
    try {
      const res = await staffApi.create({
        email: email.trim(),
        name: name.trim(),
        role,
        assignments: assignments.map((a) => ({ department: a.department, title: a.title })),
      });
      toast.success('Staff created');
      onCreated(res.user.temporary_password || '');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to create staff');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/30 p-4 pt-12">
      <div className="card relative w-full max-w-lg p-6">
        <button type="button" className="btn-ghost absolute right-2 top-2 !px-2" onClick={onClose}>
          <X className="h-5 w-5" />
        </button>
        <h2 className="mb-4 text-base font-semibold text-slate-900">Add Staff</h2>

        <div className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input className="input" placeholder="ahmad@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label">Name</label>
            <input className="input" placeholder="Ahmad" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          {canManageRole && (
            <div>
              <label className="label">Role</label>
              <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="user">User</option>
                <option value="hr_manager">HR Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          )}

          <div>
            <label className="label">Department Assignments</label>
            <div className="space-y-2">
              {assignments.map((a) => (
                <div key={a.department} className="flex items-center gap-2">
                  <span className="min-w-[120px] text-sm font-medium text-slate-700">{a.department}</span>
                  <input
                    className="input flex-1"
                    placeholder="Title (e.g. Sales Manager)"
                    value={a.title}
                    onChange={(e) =>
                      setAssignments(assignments.map((x) => (x.department === a.department ? { ...x, title: e.target.value } : x)))
                    }
                  />
                  <button type="button" className="btn-ghost !px-2 text-rose-500" onClick={() => removeAssignment(a.department)}>
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <select
                className="input"
                value=""
                onChange={(e) => { if (e.target.value) { addAssignment(e.target.value); e.target.value = ''; } }}
              >
                <option value="">+ Add department...</option>
                {departments
                  .filter((d) => !assignments.find((a) => a.department === d.name))
                  .map((d) => (
                    <option key={d.name} value={d.name}>{d.label}</option>
                  ))}
              </select>
            </div>
          </div>

          <button type="button" className="btn-primary w-full" disabled={saving} onClick={() => void handleSubmit()}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Create Staff
          </button>
        </div>
      </div>
    </div>
  );
}