import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthLayout } from "../../components/auth/AuthLayout";
import { OtpInput } from "../../components/auth/OtpInput";
import { PasswordInput } from "../../components/auth/PasswordInput";
import { PasswordStrength } from "../../components/auth/PasswordStrength";
import { GradientButton } from "../../components/ui/GradientButton";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const { resetPassword, resendOtp } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const [email, setEmail] = useState(() => localStorage.getItem("pending_reset_email") || "");
  const [otp, setOtp] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(60);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setInterval(() => setCountdown((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [countdown]);

  const handleResend = async () => {
    if (!email || countdown > 0 || resending) return;
    setError("");
    setResending(true);
    try {
      const result = await resendOtp(email, "password_reset");
      setCountdown(60);
      addToast({ title: "New reset code sent", description: result.message, type: "success" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not resend the reset code.");
    } finally {
      setResending(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter a valid email address.");
    if (!/^\d{6}$/.test(otp)) return setError("Enter the complete 6-digit reset code.");
    if (password.length < 8) return setError("New password must be at least 8 characters.");
    if (password !== confirmPassword) return setError("Passwords do not match.");
    setLoading(true);
    try {
      const message = await resetPassword(email, otp, password);
      localStorage.removeItem("pending_reset_email");
      addToast({ title: "Password updated", description: message, type: "success" });
      navigate("/login", { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Password reset failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Choose a new password" subtitle="Use the reset code from your inbox and create a strong new password.">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input-field" placeholder="Email address" />
        <OtpInput value={otp} onChange={setOtp} hasError={Boolean(error && otp.length === 6)} />
        <div className="text-center text-sm text-text-secondary">
          Didn&apos;t receive the email?{" "}
          <button type="button" disabled={countdown > 0 || resending} onClick={handleResend} className="font-semibold text-blue-300 disabled:text-text-muted">
            {resending ? "Sending..." : countdown > 0 ? `Resend in ${countdown}s` : "Resend reset code"}
          </button>
        </div>
        <PasswordInput value={password} onChange={setPassword} placeholder="New password" />
        <PasswordStrength password={password} />
        <PasswordInput value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirm new password" id="confirm-reset-password" />
        <GradientButton type="submit" loading={loading} fullWidth size="lg">{loading ? "Updating password..." : "Reset Password"}</GradientButton>
        <p className="text-center text-xs text-text-muted"><Link to="/login" className="hover:text-white">Back to sign in</Link></p>
      </form>
    </AuthLayout>
  );
}
