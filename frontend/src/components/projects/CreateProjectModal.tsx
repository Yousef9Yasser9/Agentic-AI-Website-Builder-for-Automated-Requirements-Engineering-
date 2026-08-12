import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { createProject } from "../../services/projectsService";
import { getErrorMessage } from "../../services/api";
import type { ProjectState } from "../../types/project";
import { GradientButton } from "../ui/GradientButton";

export function CreateProjectModal({
  isOpen,
  onClose,
  onCreated,
  initialIdea = "",
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (project: ProjectState) => void;
  initialIdea?: string;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [idea, setIdea] = useState(initialIdea);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && initialIdea) setIdea(initialIdea);
  }, [initialIdea, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (name.trim().length < 2) return setError("Project name must be at least 2 characters.");
    if (idea.trim().length < 20) return setError("Describe the idea in at least 20 characters.");
    setLoading(true);
    try {
      const plainText = [
        `Project name: ${name.trim()}`,
        description.trim() ? `Project summary: ${description.trim()}` : "",
        "",
        idea.trim(),
      ].filter(Boolean).join("\n");
      onCreated(await createProject(plainText));
    } catch (caught) {
      setError(getErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-black/70 p-4 backdrop-blur-sm" role="dialog" aria-modal="true">
      <form onSubmit={handleSubmit} className="glass-card w-full max-w-2xl animate-scale-in bg-surface-2/95 p-6 sm:p-8">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-300">New workspace</p>
            <h2 className="mt-2 text-2xl font-bold text-white">Create a project</h2>
            <p className="mt-2 text-sm text-text-secondary">Give the AI enough context to make the first planning stage useful.</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-xl p-2 text-text-muted hover:bg-white/5 hover:text-white" aria-label="Close modal"><X className="h-5 w-5" /></button>
        </div>
        {error ? <div className="mb-4 rounded-xl border border-danger/30 bg-danger/10 p-3 text-sm text-red-300">{error}</div> : null}
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="text-sm font-medium text-text-secondary">
            Project name
            <input value={name} onChange={(event) => setName(event.target.value)} className="input-field mt-2" placeholder="Customer support portal" autoFocus />
          </label>
          <label className="text-sm font-medium text-text-secondary">
            Short description <span className="text-text-muted">(optional)</span>
            <input value={description} onChange={(event) => setDescription(event.target.value)} className="input-field mt-2" placeholder="A portal for agents and customers" />
          </label>
        </div>
        <label className="mt-4 block text-sm font-medium text-text-secondary">
          Initial idea
          <textarea value={idea} onChange={(event) => setIdea(event.target.value)} className="input-field mt-2 min-h-40 resize-y leading-6" placeholder="Describe users, core features, roles, workflows, and any important business rules..." />
        </label>
        <div className="mt-2 text-right text-xs text-text-muted">{idea.trim().split(/\s+/).filter(Boolean).length} words</div>
        <div className="mt-6 flex justify-end gap-3">
          <GradientButton type="button" variant="ghost" onClick={onClose}>Cancel</GradientButton>
          <GradientButton type="submit" loading={loading}>{loading ? "Creating..." : "Create & Configure"}</GradientButton>
        </div>
      </form>
    </div>
  );
}
