export function PasswordStrength({ password }: { password: string }) {
  const score = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length;

  const labels = ["Weak", "Fair", "Good", "Strong"];
  const colors = ["bg-red-500", "bg-amber-500", "bg-cyan-500", "bg-emerald-500"];
  const label = password ? labels[Math.max(0, score - 1)] : "Enter password";
  const color = password ? colors[Math.max(0, score - 1)] : "bg-slate-600";

  return (
    <div className="space-y-2">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i < score ? color : "bg-white/10"}`} />
        ))}
      </div>
      <p className="text-xs text-slate-400">Strength: {label}</p>
    </div>
  );
}
