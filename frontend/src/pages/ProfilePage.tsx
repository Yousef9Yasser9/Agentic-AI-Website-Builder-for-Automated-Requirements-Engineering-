import { useState } from "react";
import { Bell, Camera, CheckCircle2, LockKeyhole, Palette, ShieldCheck, User } from "lucide-react";
import { PageWrapper } from "../components/layout/PageWrapper";
import { Badge } from "../components/ui/Badge";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { PageHeader } from "../components/ui/PageHeader";
import { PasswordInput } from "../components/auth/PasswordInput";
import { PasswordStrength } from "../components/auth/PasswordStrength";
import { useAuth } from "../contexts/AuthContext";
import { type ThemePreference, useThemeStore } from "../stores/themeStore";
import { useToastStore } from "../stores/toastStore";

type Tab = "personal" | "security" | "preferences";

export function ProfilePage() {
  const { user } = useAuth();
  const addToast = useToastStore((state) => state.addToast);
  const theme = useThemeStore((state) => state.theme);
  const setTheme = useThemeStore((state) => state.setTheme);
  const [tab, setTab] = useState<Tab>("personal");
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [notifications, setNotifications] = useState({ stages: true, builds: true, security: true });
  if (!user) return null;
  const initials = user.full_name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();

  const comingSoon = (feature: string) => addToast({ title: `${feature} is coming soon`, description: "The current backend does not expose this account update endpoint yet.", type: "info" });

  return (
    <PageWrapper>
      <PageHeader title="Profile" subtitle="Manage your account details, security options, and workspace preferences." />
      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <GlassCard padding="lg" className="h-fit text-center">
          <div className="relative mx-auto w-fit">
            <span className="grid h-28 w-28 place-items-center rounded-3xl bg-gradient-to-br from-primary to-secondary text-3xl font-bold text-white shadow-glow">{initials}</span>
            <button type="button" onClick={() => comingSoon("Avatar uploads")} className="absolute -bottom-2 -right-2 grid h-10 w-10 place-items-center rounded-xl border border-line bg-surface-2 text-text-secondary hover:text-white" aria-label="Change avatar"><Camera className="h-4 w-4" /></button>
          </div>
          <h2 className="mt-6 text-xl font-bold text-white">{user.full_name}</h2>
          <p className="mt-1 text-sm text-text-secondary">{user.email}</p>
          <div className="mt-4 flex justify-center gap-2"><Badge variant={user.role === "admin" ? "purple" : "info"}>{user.role}</Badge><Badge variant={user.is_verified ? "success" : "warning"}>{user.is_verified ? "Verified" : "Unverified"}</Badge></div>
          <div className="mt-6 border-t border-line pt-5 text-left"><p className="text-xs uppercase tracking-[0.16em] text-text-muted">Member since</p><p className="mt-2 text-sm font-semibold text-white">{new Date(user.created_at).toLocaleDateString(undefined, { dateStyle: "medium" })}</p></div>
        </GlassCard>

        <div>
          <div className="mb-5 flex gap-1 overflow-x-auto border-b border-line">
            {[
              { id: "personal" as const, label: "Personal Info", icon: User },
              { id: "security" as const, label: "Security", icon: LockKeyhole },
              { id: "preferences" as const, label: "Preferences", icon: Palette },
            ].map((item) => { const Icon = item.icon; return <button key={item.id} type="button" onClick={() => setTab(item.id)} className={`flex whitespace-nowrap border-b-2 px-4 py-3 text-sm font-semibold ${tab === item.id ? "border-primary text-white" : "border-transparent text-text-muted hover:text-text-secondary"}`}><Icon className="mr-2 h-4 w-4" />{item.label}</button>; })}
          </div>

          {tab === "personal" ? (
            <GlassCard padding="lg">
              <h2 className="text-lg font-bold text-white">Personal information</h2>
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <label className="text-sm font-medium text-text-secondary">Full name<input value={fullName} onChange={(event) => setFullName(event.target.value)} className="input-field mt-2" /></label>
                <label className="text-sm font-medium text-text-secondary">Email address<div className="relative mt-2"><input value={user.email} readOnly className="input-field pr-24 text-text-muted" /><span className="absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-1 text-xs text-success"><CheckCircle2 className="h-3.5 w-3.5" /> Verified</span></div></label>
                <label className="text-sm font-medium text-text-secondary">Role<div className="input-field mt-2 capitalize text-text-muted">{user.role}</div></label>
                <label className="text-sm font-medium text-text-secondary">Account status<div className="input-field mt-2 text-emerald-300">{user.is_active ? "Active" : "Disabled"}</div></label>
              </div>
              <GradientButton className="mt-6" onClick={() => comingSoon("Profile updates")}>Save Changes</GradientButton>
            </GlassCard>
          ) : null}

          {tab === "security" ? (
            <div className="space-y-5">
              <GlassCard padding="lg"><h2 className="text-lg font-bold text-white">Change password</h2><div className="mt-5 grid gap-4 sm:grid-cols-2"><div><PasswordInput value={newPassword} onChange={setNewPassword} placeholder="New password" /><PasswordStrength password={newPassword} /></div><PasswordInput value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirm password" id="profile-confirm-password" /></div><GradientButton className="mt-6" onClick={() => newPassword !== confirmPassword ? addToast({ title: "Passwords do not match", type: "error" }) : comingSoon("Password updates")}>Update Password</GradientButton></GlassCard>
              <GlassCard padding="lg"><div className="flex items-start justify-between gap-4"><div><h2 className="flex items-center gap-2 text-lg font-bold text-white"><ShieldCheck className="h-5 w-5 text-violet-300" /> Two-factor authentication</h2><p className="mt-2 text-sm leading-6 text-text-secondary">Add another layer of protection to your workspace account.</p></div><Badge variant="purple">Coming soon</Badge></div></GlassCard>
            </div>
          ) : null}

          {tab === "preferences" ? (
            <div className="space-y-5">
              <GlassCard padding="lg"><h2 className="text-lg font-bold text-white">Theme preference</h2><p className="mt-2 text-sm text-text-secondary">This preference is shared with Workspace Settings and saved on this device.</p><div className="mt-5 grid gap-3 sm:grid-cols-3">{(["light", "dark", "system"] as ThemePreference[]).map((option) => <button key={option} type="button" onClick={() => setTheme(option)} aria-pressed={theme === option} className={`rounded-xl border p-4 text-sm font-semibold capitalize ${theme === option ? "border-primary/40 bg-primary/10 text-blue-200" : "border-line bg-white/[0.025] text-text-secondary hover:border-line-bright"}`}>{option}</button>)}</div></GlassCard>
              <GlassCard padding="lg"><h2 className="flex items-center gap-2 text-lg font-bold text-white"><Bell className="h-5 w-5 text-blue-300" /> Notifications</h2><div className="mt-5 space-y-3">{Object.entries(notifications).map(([key, enabled]) => <label key={key} className="flex cursor-pointer items-center justify-between rounded-xl border border-line bg-white/[0.025] p-4"><span className="text-sm capitalize text-text-secondary">{key} notifications</span><input type="checkbox" checked={enabled} onChange={(event) => setNotifications((current) => ({ ...current, [key]: event.target.checked }))} className="h-5 w-5 accent-blue-500" /></label>)}</div></GlassCard>
            </div>
          ) : null}
        </div>
      </div>
    </PageWrapper>
  );
}
