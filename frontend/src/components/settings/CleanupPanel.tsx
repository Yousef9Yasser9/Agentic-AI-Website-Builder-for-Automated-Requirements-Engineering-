import { useMutation, useQuery } from "@tanstack/react-query";
import { HardDrive, Trash2 } from "lucide-react";
import { useState } from "react";
import { cleanupSystem, getSizeReport } from "../../services/settingsService";
import { GradientButton } from "../ui/GradientButton";

export function CleanupPanel() {
  const [keepApps, setKeepApps] = useState(1);
  const [keepCheckpoints, setKeepCheckpoints] = useState(5);
  const { data, refetch, isFetching } = useQuery({ queryKey: ["size-report"], queryFn: getSizeReport, enabled: false });
  const cleanup = useMutation({
    mutationFn: cleanupSystem,
    onSuccess: () => refetch(),
  });

  return (
    <div className="space-y-3">
      <GradientButton className="w-full" variant="secondary" loading={isFetching} onClick={() => refetch()}>
        <HardDrive className="h-4 w-4" />
        Size Report
      </GradientButton>
      {data?.total?.size_formatted ? (
        <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-sm text-slate-300">
          Total project size: <span className="font-semibold text-white">{data.total.size_formatted}</span>
        </div>
      ) : null}
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-slate-500">
          Apps
          <input
            className="mt-1 w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-electric/45"
            min={1}
            max={10}
            type="number"
            value={keepApps}
            onChange={(event) => setKeepApps(Number(event.target.value))}
          />
        </label>
        <label className="text-xs text-slate-500">
          Checkpoints
          <input
            className="mt-1 w-full rounded-md border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none focus:border-electric/45"
            min={1}
            max={20}
            type="number"
            value={keepCheckpoints}
            onChange={(event) => setKeepCheckpoints(Number(event.target.value))}
          />
        </label>
      </div>
      <GradientButton
        className="w-full"
        variant="danger"
        loading={cleanup.isPending}
        onClick={() => cleanup.mutate({ keep_apps: keepApps, keep_checkpoints: keepCheckpoints })}
      >
        <Trash2 className="h-4 w-4" />
        Run Cleanup
      </GradientButton>
    </div>
  );
}

