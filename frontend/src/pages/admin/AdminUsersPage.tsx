import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AdminLayout } from "../../components/layout/AdminLayout";
import { GlassCard } from "../../components/ui/GlassCard";
import { LoadingState } from "../../components/ui/LoadingState";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { fetchAdminUsers, updateAdminUser } from "../../services/adminService";
import { useAuth } from "../../contexts/AuthContext";

export function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-users"], queryFn: fetchAdminUsers });

  const mutation = useMutation({
    mutationFn: ({ userId, payload }: { userId: number; payload: { is_active?: boolean; role?: "user" | "admin" } }) =>
      updateAdminUser(userId, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  if (isLoading) return <AdminLayout title="Users"><LoadingState label="Loading users..." /></AdminLayout>;

  return (
    <AdminLayout title="User Management" subtitle="Manage roles, verification, and account status">
      <GlassCard className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 border-b border-white/10">
              <th className="text-left p-4">Name</th>
              <th className="text-left p-4">Email</th>
              <th className="text-left p-4">Role</th>
              <th className="text-left p-4">Verified</th>
              <th className="text-left p-4">Status</th>
              <th className="text-left p-4">Created</th>
              <th className="text-left p-4">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((user) => {
              const isSelf = user.id === currentUser?.id;
              return (
                <tr key={user.id} className="border-b border-white/5">
                  <td className="p-4 text-white">{user.full_name}</td>
                  <td className="p-4 text-slate-400">{user.email}</td>
                  <td className="p-4"><StatusBadge tone="current">{user.role}</StatusBadge></td>
                  <td className="p-4"><StatusBadge tone={user.is_verified ? "success" : "warning"}>{user.is_verified ? "Yes" : "No"}</StatusBadge></td>
                  <td className="p-4"><StatusBadge tone={user.is_active ? "success" : "error"}>{user.is_active ? "Active" : "Blocked"}</StatusBadge></td>
                  <td className="p-4 text-slate-400">{new Date(user.created_at).toLocaleDateString()}</td>
                  <td className="p-4">
                    <div className="flex flex-wrap gap-2">
                      {!isSelf && (
                        <button
                          onClick={() => mutation.mutate({ userId: user.id, payload: { is_active: !user.is_active } })}
                          className="px-3 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-white"
                        >
                          {user.is_active ? "Disable" : "Enable"}
                        </button>
                      )}
                      {!isSelf && (
                        <button
                          onClick={() =>
                            mutation.mutate({
                              userId: user.id,
                              payload: { role: user.role === "admin" ? "user" : "admin" },
                            })
                          }
                          className="px-3 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-xs text-cyan-300"
                        >
                          {user.role === "admin" ? "Demote" : "Promote"}
                        </button>
                      )}
                      {isSelf && <span className="text-xs text-slate-500">You</span>}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </GlassCard>
    </AdminLayout>
  );
}
