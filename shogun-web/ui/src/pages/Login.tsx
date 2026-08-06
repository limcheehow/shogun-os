import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { authApi, ApiError } from "../lib/api";
import { PublicOnlyRoute, useAuth } from "../lib/auth";
import logoBlue from "../assets/logos/samurai-logo-blue.png";

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

function MailIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <rect x="5" y="11" width="14" height="9" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </svg>
  );
}

function EyeIcon({ open }: { open: boolean }) {
  return open ? (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path d="M3 3l18 18" />
      <path d="M10.6 5.2A10.7 10.7 0 0 1 12 5c6.5 0 10 7 10 7a17.7 17.7 0 0 1-3.2 4.1M6.6 6.6C4 8.3 2 12 2 12s3.5 7 10 7a9.8 9.8 0 0 0 3.4-.6" />
      <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
    </svg>
  );
}

function LoginInner() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [keepSignedIn, setKeepSignedIn] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fillDemoCredentials = () => {
    setEmail("admin@localhost");
    setPassword("admin123456");
    toast.success("Admin demo credentials filled!");
  };

  const handleForgotPassword = () => {
    toast(
      "Please contact your Shogun OS administrator to reset your account password.",
      {
        icon: "ℹ️",
        duration: 5000,
      },
    );
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = await login({ email: email.trim(), password, keepSignedIn });
      toast.success(`Welcome back, ${user.name || "Operator"}!`);
      if (user.must_change_password)
        navigate("/change-password", { replace: true });
      else if (user.first_login) navigate("/onboarding", { replace: true });
      else navigate("/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Login failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="sd-login-page" id="login-page">
      <div className="sd-login-shell">
        <section className="sd-hero-panel" aria-labelledby="sd-hero-title">
          <div className="sd-hero-overlay" aria-hidden />
          <div className="sd-hero-content">
            <img
              className="sd-hero-logo"
              src={logoBlue}
              alt="SamurAI"
              width={230}
              height={48}
            />
            <div className="sd-hero-copy">
              <p className="sd-hero-kicker">Shogun OS · Command Portal</p>
              <h1 id="sd-hero-title">
                One company
                <span className="block">Multiple AI-operated departments</span>
              </h1>
              <p className="sd-hero-lede">
                Shogun OS deploys your organization as isolated agent profiles —
                each with its own persona, knowledge source, and Slack bot —
                coordinated through a single command portal.
              </p>
            </div>
            <ul className="sd-hero-stats" aria-label="Key features">
              <li>Hermes Agent profiles</li>
              <li>GBrain federated memory</li>
              <li>Per-department dashboards</li>
              <li>Slack-native operations</li>
            </ul>
          </div>
        </section>

        <div className="sd-form-panel">
          <div className="sd-form-card">
            <div className="sd-form-header">
              <h2>Welcome back</h2>
              <p className="sd-form-subtext">Sign in to your company portal</p>
            </div>

            <div className="sd-sso-row">
              <a href={authApi.oauthUrl("google")} className="sd-sso-btn">
                <GoogleIcon />
                Continue with Google
              </a>
              <a href={authApi.oauthUrl("microsoft")} className="sd-sso-btn">
                <MicrosoftIcon />
                Continue with Microsoft
              </a>
            </div>

            <div className="sd-divider">or sign in with email</div>

            {/* Local Demo Fill Helper */}
            <div className="mb-4 flex items-center justify-between rounded-xl border border-indigo-500/20 bg-indigo-500/10 p-2.5 text-xs text-indigo-300">
              <span className="truncate">
                ⚡ Testing locally? Click to fill admin account.
              </span>
              <button
                type="button"
                onClick={fillDemoCredentials}
                className="ml-2 shrink-0 rounded-lg bg-indigo-600 px-2.5 py-1 text-xs font-semibold text-white transition hover:bg-indigo-500 active:scale-95"
              >
                Fill Admin
              </button>
            </div>

            <form onSubmit={onSubmit} noValidate>
              {error && (
                <p role="alert" aria-live="polite" className="sd-error-alert">
                  {error}
                </p>
              )}

              <div className="sd-field-group">
                <label className="sd-label" htmlFor="sd-email">
                  Email
                </label>
                <div className="sd-input-wrap">
                  <span className="sd-input-icon">
                    <MailIcon />
                  </span>
                  <input
                    id="sd-email"
                    className="sd-input"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="admin@localhost"
                  />
                </div>
              </div>

              <div className="sd-field-group">
                <div className="flex items-center justify-between mb-1.5">
                  <label className="sd-label mb-0" htmlFor="sd-password">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={handleForgotPassword}
                    className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="sd-input-wrap">
                  <span className="sd-input-icon">
                    <LockIcon />
                  </span>
                  <input
                    id="sd-password"
                    className="sd-input has-toggle"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    className="sd-input-toggle"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                  >
                    <EyeIcon open={showPassword} />
                  </button>
                </div>
              </div>

              <div className="sd-form-row">
                <label className="sd-checkbox-label">
                  <input
                    type="checkbox"
                    checked={keepSignedIn}
                    onChange={(e) => setKeepSignedIn(e.target.checked)}
                  />
                  Keep me signed in
                </label>
              </div>

              <button
                type="submit"
                className="sd-submit-btn"
                disabled={loading}
              >
                {loading ? "Signing in…" : "Sign in"}
              </button>
            </form>

            <div className="sd-form-footer">
              Shogun OS · Enterprise-grade multi-agent operations
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function Login() {
  return (
    <PublicOnlyRoute>
      <LoginInner />
    </PublicOnlyRoute>
  );
}
