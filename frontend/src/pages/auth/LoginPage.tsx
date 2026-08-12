import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Mail } from "lucide-react";
import { AuthLayout } from "../../components/auth/AuthLayout";
import { PasswordInput } from "../../components/auth/PasswordInput";
import { GradientButton } from "../../components/ui/GradientButton";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter a valid email address.");
    if (!password) return setError("Password is required.");
    setLoading(true);
    try {
      const loggedInUser = await login(email.trim(), password);
      if (!remember) sessionStorage.setItem("temporary_session", "true");
      addToast({ title: "Welcome back", description: `Signed in as ${loggedInUser.full_name}.`, type: "success" });
      const requestedPath = (location.state as { from?: string } | null)?.from;
      navigate(requestedPath || (loggedInUser.role === "admin" ? "/admin" : "/dashboard"), { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue building production-ready applications."
      footer={<>Don&apos;t have an account? <Link to="/register" className="font-semibold text-blue-300 hover:text-blue-200">Create one</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        {error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        <div>
          <label htmlFor="login-email" className="mb-2 block text-sm font-medium text-text-secondary">Email address</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <input id="login-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={`input-field pl-10 ${error && !email ? "border-danger/60" : ""}`} placeholder="you@example.com" autoComplete="email" />
          </div>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-medium text-text-secondary">Password</label>
            <Link to="/forgot-password" className="text-xs font-semibold text-blue-300 hover:text-blue-200">Forgot password?</Link>
          </div>
          <PasswordInput value={password} onChange={setPassword} />
        </div>
        <label className="flex cursor-pointer items-center gap-2.5 text-sm text-text-secondary">
          <input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} className="h-4 w-4 rounded border-white/20 bg-white/5 accent-blue-500" />
          Remember me on this device
        </label>
        <GradientButton type="submit" loading={loading} fullWidth size="lg">
          {loading ? "Signing in..." : "Sign In"}
        </GradientButton>
      </form>
    </AuthLayout>
  );
}
