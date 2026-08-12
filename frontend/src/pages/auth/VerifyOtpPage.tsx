import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { AuthLayout } from "../../components/auth/AuthLayout";
import { OtpInput } from "../../components/auth/OtpInput";
import { GradientButton } from "../../components/ui/GradientButton";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";

export function VerifyOtpPage() {
  const navigate = useNavigate();
  const { verifyOtp, resendOtp } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const [email, setEmail] = useState(() => localStorage.getItem("pending_verify_email") || "");
  const [otp, setOtp] = useState(() => localStorage.getItem("pending_verify_otp") || "");
  const [developmentCode, setDevelopmentCode] = useState(() => Boolean(localStorage.getItem("pending_verify_otp")));
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [countdown, setCountdown] = useState(60);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setInterval(() => setCountdown((current) => Math.max(0, current - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [countdown]);

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter the email used during registration.");
    if (!/^\d{6}$/.test(otp)) return setError("Enter the complete 6-digit code.");
    setLoading(true);
    try {
      const verifiedUser = await verifyOtp(email, otp, "register_verification");
      localStorage.removeItem("pending_verify_email");
      localStorage.removeItem("pending_verify_otp");
      addToast({ title: "Email verified", description: "Your workspace is ready.", type: "success" });
      navigate(verifiedUser?.role === "admin" ? "/admin" : "/dashboard", { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Verification failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (!email || countdown > 0) return;
    try {
      const result = await resendOtp(email, "register_verification");
      if (result.dev_otp) {
        localStorage.setItem("pending_verify_otp", result.dev_otp);
        setOtp(result.dev_otp);
        setDevelopmentCode(true);
      } else {
        localStorage.removeItem("pending_verify_otp");
        setDevelopmentCode(false);
      }
      setCountdown(60);
      addToast({ title: result.dev_otp ? "New local code loaded" : "New code sent", description: result.message, type: "success" });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not resend the code.");
    }
  };

  return (
    <AuthLayout
      title="Check your inbox"
      subtitle={`We sent a six-digit verification code${email ? ` to ${email}` : ""}.`}
      steps={[{ label: "Register", active: false, done: true }, { label: "Verify", active: true, done: false }, { label: "Build", active: false, done: false }]}
    >
      <form onSubmit={handleVerify} className="space-y-5">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white shadow-glow"><MailCheck className="h-6 w-6" /></div>
        {error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        {developmentCode ? <div className="rounded-xl border border-primary/20 bg-primary/10 p-3 text-center text-xs text-blue-300">Local development mode: the verification code is pre-filled because SMTP is not configured.</div> : null}
        {!email ? <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input-field" placeholder="Email address" /> : null}
        <OtpInput value={otp} onChange={setOtp} hasError={Boolean(error && otp.length === 6)} />
        <GradientButton type="submit" loading={loading} fullWidth size="lg">{loading ? "Verifying..." : "Verify Email"}</GradientButton>
        <div className="text-center text-sm text-text-secondary">
          Didn&apos;t receive it?{" "}
          <button type="button" disabled={countdown > 0} onClick={handleResend} className="font-semibold text-blue-300 disabled:text-text-muted">
            {countdown > 0 ? `Resend in ${countdown}s` : "Resend Code"}
          </button>
        </div>
        <p className="text-center text-xs text-text-muted"><Link to="/login" className="hover:text-white">Back to sign in</Link></p>
      </form>
    </AuthLayout>
  );
}
