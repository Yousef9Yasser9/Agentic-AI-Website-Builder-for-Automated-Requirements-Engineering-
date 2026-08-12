import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { GlassCard } from "../../components/ui/GlassCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { fetchAdminProjects } from "../../services/adminService";

export function AdminProjectsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["admin-projects"], queryFn: fetchAdminProjects });

  if (isLoading) return <AdminLayout title="All Projects"><LoadingState label="Loading projects..." /></AdminLayout>;

  return (
    <AdminLayout title="All Projects" subtitle="Every project across all users">
      <GlassCard className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-white/10">
              <th className="text-left p-4">Title</th>
              <th className="text-left p-4">Project ID</th>
              <th className="text-left p-4">Owner ID</th>
              <th className="text-left p-4">Stage</th>
              <th className="text-left p-4">Progress</th>
              <th className="text-left p-4">App Status</th>
              <th className="text-left p-4">Updated</th>
              <th className="text-left p-4">Open</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((project) => (
              <tr key={project.project_id} className="border-b border-white/5">
                <td className="p-4 text-white">{project.project_title}</td>
                <td className="p-4 text-slate-400 font-mono">{project.project_id}</td>
                <td className="p-4 text-slate-400">{project.owner_user_id ?? "legacy"}</td>
                <td className="p-4 text-cyan-400">{project.stage}</td>
                <td className="p-4 text-white">{project.completion_percent}%</td>
                <td className="p-4 text-purple-300">{project.generated_app_status}</td>
                <td className="p-4 text-slate-400">{project.saved_at ? new Date(project.saved_at).toLocaleString() : "-"}</td>
                <td className="p-4">
                  <Link to={`/admin/projects/${project.project_id}`} className="text-cyan-400 hover:text-cyan-300">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </GlassCard>
    </AdminLayout>
  );
}
