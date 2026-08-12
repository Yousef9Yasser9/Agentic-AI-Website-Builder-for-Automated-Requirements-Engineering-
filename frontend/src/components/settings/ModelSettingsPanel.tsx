import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import type { ModelSettings } from "../../types/project";
import { getErrorMessage } from "../../services/api";
import { getModelSettings, updateModelSettings } from "../../services/settingsService";
import { GradientButton } from "../ui/GradientButton";
import { ErrorState } from "../ui/ErrorState";

const inputClass =
  "w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-electric/45";

export function ModelSettingsPanel() {
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ["model-settings"], queryFn: getModelSettings });
  const [form, setForm] = useState<ModelSettings | undefined>();
  const mutation = useMutation({
    mutationFn: updateModelSettings,
    onSuccess: (settings) => queryClient.setQueryData(["model-settings"], settings),
  });

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  if (!form) return null;

  const update = (key: keyof ModelSettings, value: string | number) => {
    setForm((current) => (current ? { ...current, [key]: value } : current));
  };

  return (
    <div className="space-y-3">
      <div className="grid gap-3">
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Architect Model</label>
        <input className={inputClass} value={form.model_architect} onChange={(event) => update("model_architect", event.target.value)} />
        <label className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Coder Model</label>
        <input className={inputClass} value={form.model_coder} onChange={(event) => update("model_coder", event.target.value)} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <input
          className={inputClass}
          type="number"
          value={form.model_ctx_architect}
          onChange={(event) => update("model_ctx_architect", Number(event.target.value))}
          title="Architect context"
        />
        <input
          className={inputClass}
          type="number"
          value={form.model_ctx_coder}
          onChange={(event) => update("model_ctx_coder", Number(event.target.value))}
          title="Coder context"
        />
        <input
          className={inputClass}
          type="number"
          value={form.model_ctx_reviewer}
          onChange={(event) => update("model_ctx_reviewer", Number(event.target.value))}
          title="Reviewer context"
        />
      </div>
      {mutation.isError ? <ErrorState message={getErrorMessage(mutation.error)} /> : null}
      <GradientButton className="w-full" variant="secondary" loading={mutation.isPending} onClick={() => mutation.mutate(form)}>
        <Save className="h-4 w-4" />
        Save Models
      </GradientButton>
    </div>
  );
}

