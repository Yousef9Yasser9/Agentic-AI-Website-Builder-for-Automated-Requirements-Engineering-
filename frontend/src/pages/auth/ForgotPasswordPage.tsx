import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Mail } from "lucide-react";
import { AuthLayout } from "../../components/auth/AuthLayout";
import { GradientButton } from "../../components/ui/GradientButton";
import { useAuth } from "../../contexts/AuthContext";
import { useToastStore } from "../../stores/toastStore";

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const { forgotPassword } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError("Enter a valid email address.");
    setLoading(true);
    try {
      const message = await forgotPassword(email.trim());
      localStorage.setItem("pending_reset_email", email.trim());
      addToast({ title: "Reset code requested", description: message, type: "success" });
      navigate("/reset-password");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not request a reset code.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Reset your password" subtitle="Enter your email and we will send a secure reset code.">
      <form onSubmit={handleSubmit} className="space-y-5">
        {error ? <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        <div>
          <label htmlFor="reset-email" className="mb-2 block text-sm font-medium text-text-secondary">Email address</label>
          <div className="relative">
            <Mail className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <input id="reset-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="input-field pl-10" placeholder="you@example.com" />
          </div>
        </div>
        <GradientButton type="submit" loading={loading} fullWidth size="lg">{loading ? "Sending code..." : "Send Reset Code"}</GradientButton>
        <Link to="/login" className="flex items-center justify-center gap-2 text-sm text-text-secondary hover:text-white"><ArrowLeft className="h-4 w-4" /> Back to login</Link>
      </form>
    </AuthLayout>
  );
}
