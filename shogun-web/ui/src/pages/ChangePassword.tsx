import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { ApiError, authApi } from '../lib/api';
import { useAuth } from '../lib/auth';

export default function ChangePassword() {
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      await refreshUser();
      toast.success('Password updated');
      navigate('/onboarding', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-muted px-4 py-10">
      <div className="card w-full max-w-md p-8">
        <h1 className="text-xl font-semibold text-slate-900">Change your password</h1>
        <p className="mt-1 text-sm text-slate-500">
          For security, you must set a new password before continuing.
        </p>

        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          )}

          <div>
            <label className="label" htmlFor="current">
              Current password
            </label>
            <input
              id="current"
              type="password"
              className="input"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>

          <div>
            <label className="label" htmlFor="new">
              New password
            </label>
            <input
              id="new"
              type="password"
              className="input"
              required
              minLength={8}
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-400">Minimum 8 characters</p>
          </div>

          <div>
            <label className="label" htmlFor="confirm">
              Confirm new password
            </label>
            <input
              id="confirm"
              type="password"
              className="input"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Update password
          </button>
        </form>
      </div>
    </div>
  );
}
