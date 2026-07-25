import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { authApi } from '../lib/api';
import { PublicOnlyRoute, useAuth } from '../lib/auth';
import { ApiError } from '../lib/api';

function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden>
      <path
        fill="#EA4335"
        d="M12 10.2v3.6h5.1c-.2 1.2-1.5 3.6-5.1 3.6-3.1 0-5.6-2.5-5.6-5.6S8.9 6.2 12 6.2c1.8 0 3 .7 3.7 1.4l2.5-2.4C16.7 3.7 14.6 2.7 12 2.7 6.9 2.7 2.7 6.9 2.7 12S6.9 21.3 12 21.3c5.5 0 9.1-3.9 9.1-9.3 0-.6-.1-1.1-.2-1.8H12z"
      />
      <path
        fill="#34A853"
        d="M3.9 7.3l3 2.2C7.7 7.5 9.7 6.2 12 6.2c1.8 0 3 .7 3.7 1.4l2.5-2.4C16.7 3.7 14.6 2.7 12 2.7 8.5 2.7 5.4 4.7 3.9 7.3z"
      />
      <path
        fill="#4A90E2"
        d="M12 21.3c2.5 0 4.6-.8 6.1-2.2l-2.9-2.3c-.8.5-1.8.9-3.2.9-2.5 0-4.6-1.7-5.3-3.9l-3 2.3c1.5 3 4.5 5.2 8.3 5.2z"
      />
      <path
        fill="#FBBC05"
        d="M6.7 13.8c-.2-.5-.3-1.1-.3-1.8s.1-1.3.3-1.8l-3-2.3C3.2 9.2 2.7 10.5 2.7 12s.5 2.8 1.2 4l2.8-2.2z"
      />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 23 23" aria-hidden>
      <path fill="#f35325" d="M1 1h10v10H1z" />
      <path fill="#81bc06" d="M12 1h10v10H12z" />
      <path fill="#05a6f0" d="M1 12h10v10H1z" />
      <path fill="#ffba08" d="M12 12h10v10H12z" />
    </svg>
  );
}

function LoginInner() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login({ email: email.trim(), password });
      if (user.must_change_password) navigate('/change-password', { replace: true });
      else if (user.first_login) navigate('/onboarding', { replace: true });
      else navigate('/dashboard', { replace: true });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Login failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-50 via-white to-indigo-50 px-4 py-10">
      <div className="w-full max-w-md">
        <div className="card p-8">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand text-2xl font-bold text-white shadow-sm">
              S
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Shogun OS</h1>
            <p className="mt-1 text-sm text-slate-500">Sign in to your company portal</p>
          </div>

          <div className="space-y-3">
            <a href={authApi.oauthUrl('google')} className="btn-secondary w-full">
              <GoogleIcon />
              Continue with Google
            </a>
            <a href={authApi.oauthUrl('microsoft')} className="btn-secondary w-full">
              <MicrosoftIcon />
              Continue with Microsoft
            </a>
          </div>

          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-surface-border" />
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
              or sign in with email
            </span>
            <div className="h-px flex-1 bg-surface-border" />
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            {error && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {error}
              </div>
            )}

            <div>
              <label className="label" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </div>

            <div>
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              Sign in
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default function Login() {
  return (
    <PublicOnlyRoute>
      <LoginInner />
    </PublicOnlyRoute>
  );
}
