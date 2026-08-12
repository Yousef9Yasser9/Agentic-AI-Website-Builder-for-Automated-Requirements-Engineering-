import { Routes, Route, Navigate } from "react-router-dom";
import { AdminRoute } from "../components/routes/AdminRoute";
import { ProtectedRoute } from "../components/routes/ProtectedRoute";
import { PublicRoute } from "../components/routes/PublicRoute";
import { useAuth } from "../contexts/AuthContext";
import { AppLayout } from "../components/layout/AppLayout";
import { LandingPage } from "../pages/LandingPage";
import { BuilderPage } from "../pages/BuilderPage";
import { ProjectsPage } from "../pages/ProjectsPage";
import { ProjectDetailsPage } from "../pages/ProjectDetailsPage";
import { DashboardPage } from "../pages/DashboardPage";
import { GeneratedAppsPage } from "../pages/GeneratedAppsPage";
import { TemplatesPage } from "../pages/TemplatesPage";
import { DocsPage } from "../pages/DocsPage";
import { ProfilePage } from "../pages/ProfilePage";
import { SettingsPage } from "../pages/SettingsPage";
import { LoginPage } from "../pages/auth/LoginPage";
import { RegisterPage } from "../pages/auth/RegisterPage";
import { VerifyOtpPage } from "../pages/auth/VerifyOtpPage";
import { ForgotPasswordPage } from "../pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "../pages/auth/ResetPasswordPage";
import { AdminUsersPage } from "../pages/admin/AdminUsersPage";
import { AdminDashboardPage } from "../pages/admin/AdminDashboardPage";
import { AdminProjectsPage } from "../pages/admin/AdminProjectsPage";
import { AdminGeneratedAppsPage } from "../pages/admin/AdminGeneratedAppsPage";
import { AdminSystemPage } from "../pages/admin/AdminSystemPage";
import { AdminModelsPage } from "../pages/admin/AdminModelsPage";
import { AdminLogsPage } from "../pages/admin/AdminLogsPage";

function UserRoute({ children }: { children: React.ReactNode }) {
  const { isAdmin } = useAuth();
  return isAdmin ? <Navigate to="/admin" replace /> : <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />

      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route path="/verify-otp" element={<VerifyOtpPage />} />
      <Route path="/forgot-password" element={<PublicRoute><ForgotPasswordPage /></PublicRoute>} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route path="/dashboard" element={<UserRoute><DashboardPage /></UserRoute>} />
        <Route path="/builder" element={<UserRoute><BuilderPage /></UserRoute>} />
        <Route path="/projects" element={<UserRoute><ProjectsPage /></UserRoute>} />
        <Route path="/projects/:id" element={<UserRoute><ProjectDetailsPage /></UserRoute>} />
        <Route path="/generated-apps" element={<UserRoute><GeneratedAppsPage /></UserRoute>} />
        <Route path="/templates" element={<UserRoute><TemplatesPage /></UserRoute>} />
        <Route path="/docs" element={<UserRoute><DocsPage /></UserRoute>} />
        <Route path="/profile" element={<UserRoute><ProfilePage /></UserRoute>} />
        <Route path="/settings" element={<UserRoute><SettingsPage /></UserRoute>} />
        <Route path="/admin" element={<AdminRoute><AdminDashboardPage /></AdminRoute>} />
        <Route path="/admin/users" element={<AdminRoute><AdminUsersPage /></AdminRoute>} />
        <Route path="/admin/projects" element={<AdminRoute><AdminProjectsPage /></AdminRoute>} />
        <Route path="/admin/projects/:id" element={<AdminRoute><ProjectDetailsPage /></AdminRoute>} />
        <Route path="/admin/generated-apps" element={<AdminRoute><AdminGeneratedAppsPage /></AdminRoute>} />
        <Route path="/admin/system" element={<AdminRoute><AdminSystemPage /></AdminRoute>} />
        <Route path="/admin/models" element={<AdminRoute><AdminModelsPage /></AdminRoute>} />
        <Route path="/admin/logs" element={<AdminRoute><AdminLogsPage /></AdminRoute>} />
      </Route>

      <Route path="/system" element={<Navigate to="/admin/system" replace />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
