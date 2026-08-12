import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Mail, User } from "lucide-react";
import { AuthLayout } from "../../components/auth/AuthLayout";
import { PasswordInput } from "../../components/auth/PasswordInput";
import { PasswordStrength } from "../../components/auth/PasswordStrength";
import { GradientButton } from "../../components/ui/GradientButton";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (fullName.trim().length < 2) return setError("Enter your full name.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter a valid email address.");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    if (password !== confirmPassword) return setError("Passwords do not match.");
    if (!accepted) return setError("Please accept the Terms of Service and Privacy Policy.");

    setLoading(true);
    try {
      const result = await register(fullName.trim(), email.trim(), password);
      localStorage.setItem("pending_verify_email", email.trim());
      localStorage.removeItem("pending_verify_otp");
      if (result.dev_otp) localStorage.setItem("pending_verify_otp", result.dev_otp);
      addToast({
        title: result.dev_otp ? "Local verification code ready" : "Check your inbox",
        description: result.dev_otp ? "SMTP is not configured, so the development code was loaded automatically." : result.message,
        type: "success",
      });
      navigate("/verify-otp");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start with a free workspace and turn your next idea into a real application."
      steps={[{ label: "Register", active: true, done: false }, { label: "Verify", active: false, done: false }, { label: "Build", active: false, done: false }]}
      footer={<>Already have an account? <Link to="/login" className="font-semibold text-blue-300 hover:text-blue-200">Sign in</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        <div className="relative">
          <User className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input value={fullName} onChange={(event) => setFullName(event.target.value)} placeholder="Full name" className="input-field pl-10" autoComplete="name" />
        </div>
        <div className="relative">
          <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email address" className="input-field pl-10" autoComplete="email" />
        </div>
        <PasswordInput value={password} onChange={setPassword} placeholder="Password" />
        <PasswordStrength password={password} />
        <PasswordInput value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirm password" id="confirm-password" />
        <label className="flex cursor-pointer items-start gap-2.5 text-xs leading-5 text-text-secondary">
          <input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} className="mt-0.5 h-4 w-4 rounded border-white/20 bg-white/5 accent-blue-500" />
          <span>I agree to the <button type="button" className="text-blue-300">Terms of Service</button> and <button type="button" className="text-blue-300">Privacy Policy</button>.</span>
        </label>
        <GradientButton type="submit" loading={loading} fullWidth size="lg">{loading ? "Creating account..." : "Create Account"}</GradientButton>
      </form>
    </AuthLayout>
  );
}
