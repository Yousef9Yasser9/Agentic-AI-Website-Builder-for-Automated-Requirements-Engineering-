import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Server,
  Cpu,
  HardDrive,
  Activity,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Trash2,
  Database,
  Folder,
  Code,
  Settings,
  Zap,
  Clock,
  TrendingUp,
  Info,
  Terminal,
} from "lucide-react";
import { Navbar } from "../components/layout/Navbar";
import { GlassCard } from "../components/ui/GlassCard";
import { GradientButton } from "../components/ui/GradientButton";
import { LoadingState } from "../components/ui/LoadingState";
import { api } from "../services/api";

export function SystemPage() {
  const queryClient = useQueryClient();

  const { data: ollamaStatus, isLoading: statusLoading } = useQuery({
    queryKey: ["ollama-status"],
    queryFn: async () => {
      const response = await api.get("/api/settings/ollama/status");
      return response.data;
    },
    refetchInterval: 5000,
  });

  const { data: modelSettings, isLoading: settingsLoading } = useQuery({
    queryKey: ["model-settings"],
    queryFn: async () => {
      const response = await api.get("/api/settings/models");
      return response.data;
    },
  });

  const { data: systemInfo } = useQuery({
    queryKey: ["system-info"],
    queryFn: async () => {
      // Mock system info - replace with real API call
      return {
        cpu_usage: 45,
        memory_total: 16,
        memory_used: 8.5,
        disk_total: 512,
        disk_used: 310,
        checkpoints_size: 2.4,
        generated_apps_size: 5.8,
        uptime: "3 days 14 hours",
      };
    },
    refetchInterval: 10000,
  });

  const cleanupMutation = useMutation({
    mutationFn: async (type: "checkpoints" | "generated" | "all") => {
      const response = await api.post("/api/system/cleanup", { type });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["system-info"] });
    },
  });

  const memoryPercent = systemInfo ? (systemInfo.memory_used / systemInfo.memory_total) * 100 : 0;
  const diskPercent = systemInfo ? (systemInfo.disk_used / systemInfo.disk_total) * 100 : 0;

  const modelInfo = [
    {
      name: "Architect Model",
      model: modelSettings?.model_architect || "llama3.1:8b",
      purpose: "Requirements, User Stories, Architecture",
      color: "from-cyan-500 to-blue-500",
      icon: Code,
    },
    {
      name: "Coder Model",
      model: modelSettings?.model_coder || "qwen2.5-coder:14b",
      purpose: "Code Generation, Refactoring, Tests",
      color: "from-purple-500 to-pink-500",
      icon: Terminal,
    },
  ];

  const resourceMetrics = [
    {
      label: "CPU Usage",
      value: systemInfo?.cpu_usage || 0,
      max: 100,
      unit: "%",
      icon: Cpu,
      color: "from-cyan-500 to-blue-500",
      status: (systemInfo?.cpu_usage || 0) > 80 ? "warning" : "normal",
    },
    {
      label: "Memory",
      value: memoryPercent,
      max: 100,
      unit: "%",
      details: `${systemInfo?.memory_used || 0} / ${systemInfo?.memory_total || 0} GB`,
      icon: Activity,
      color: "from-purple-500 to-pink-500",
      status: memoryPercent > 85 ? "warning" : "normal",
    },
    {
      label: "Disk Space",
      value: diskPercent,
      max: 100,
      unit: "%",
      details: `${systemInfo?.disk_used || 0} / ${systemInfo?.disk_total || 0} GB`,
      icon: HardDrive,
      color: "from-green-500 to-emerald-500",
      status: diskPercent > 90 ? "warning" : "normal",
    },
  ];

  if (statusLoading || settingsLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
        <Navbar />
        <div className="container mx-auto px-6 pt-24">
          <LoadingState label="Loading system information..." />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <Navbar />
      
      <div className="container mx-auto px-6 pt-24 pb-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl font-bold text-white mb-3 flex items-center gap-3">
                <Server className="w-10 h-10 text-cyan-400" />
                System Health
              </h1>
              <p className="text-lg text-slate-400">
                Monitor AI models, resources, and system performance
              </p>
            </div>
            <GradientButton onClick={() => queryClient.invalidateQueries()}>
              <RefreshCw className="w-5 h-5 mr-2" />
              Refresh All
            </GradientButton>
          </div>
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-6 mb-12">
          {/* Ollama Status */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2"
          >
            <GlassCard className={`p-6 ${ollamaStatus?.online ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center gap-4">
                  <div className={`p-4 rounded-xl ${ollamaStatus?.online ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                    <Server className={`w-8 h-8 ${ollamaStatus?.online ? 'text-green-400' : 'text-red-400'}`} />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">Ollama AI Service</h2>
                    <p className="text-sm text-slate-400">Local AI model server</p>
                  </div>
                </div>
                <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
                  ollamaStatus?.online 
                    ? 'bg-green-500/20 text-green-400' 
                    : 'bg-red-500/20 text-red-400'
                }`}>
                  {ollamaStatus?.online ? (
                    <>
                      <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                      <span className="font-semibold">Online</span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-4 h-4" />
                      <span className="font-semibold">Offline</span>
                    </>
                  )}
                </div>
              </div>

              {ollamaStatus?.online ? (
                <div className="grid md:grid-cols-2 gap-4">
                  {modelInfo.map((model, index) => {
                    const Icon = model.icon;
                    return (
                      <div key={index} className="p-4 rounded-xl bg-white/5 border border-white/10">
                        <div className="flex items-center gap-3 mb-3">
                          <div className={`p-2 rounded-lg bg-gradient-to-br ${model.color}`}>
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h3 className="font-semibold text-white">{model.name}</h3>
                            <p className="text-xs text-slate-400">{model.purpose}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                          <code className="px-2 py-1 rounded bg-slate-950/50 text-cyan-400 font-mono">
                            {model.model}
                          </code>
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8">
                  <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">Ollama Service Not Available</h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Make sure Ollama is installed and running on your system
                  </p>
                  <button className="px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium hover:bg-red-500/20 transition-colors">
                    View Setup Guide
                  </button>
                </div>
              )}
            </GlassCard>
          </motion.div>

          {/* System Uptime */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <GlassCard className="p-6 h-full">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-3 rounded-xl bg-gradient-to-br from-orange-500 to-red-500">
                  <Clock className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-white">System Uptime</h3>
                  <p className="text-xs text-slate-400">Since last restart</p>
                </div>
              </div>
              <div className="text-3xl font-bold text-white mb-4">
                {systemInfo?.uptime || "0 days"}
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between text-slate-400">
                  <span>Status:</span>
                  <span className="text-green-400">Healthy</span>
                </div>
                <div className="flex justify-between text-slate-400">
                  <span>Last Check:</span>
                  <span className="text-white">Just now</span>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        </div>

        {/* Resource Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-12"
        >
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
            <TrendingUp className="w-6 h-6 text-purple-400" />
            Resource Usage
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {resourceMetrics.map((metric, index) => {
              const Icon = metric.icon;
              return (
                <motion.div
                  key={metric.label}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 + index * 0.1 }}
                >
                  <GlassCard className={`p-6 ${metric.status === 'warning' ? 'border-yellow-500/30 bg-yellow-500/5' : ''}`}>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`p-3 rounded-xl bg-gradient-to-br ${metric.color}`}>
                          <Icon className="w-6 h-6 text-white" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{metric.label}</h3>
                          {metric.details && (
                            <p className="text-xs text-slate-400">{metric.details}</p>
                          )}
                        </div>
                      </div>
                      {metric.status === 'warning' && (
                        <AlertCircle className="w-5 h-5 text-yellow-400" />
                      )}
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-400">Current</span>
                        <span className="text-2xl font-bold text-white">
                          {Math.round(metric.value)}{metric.unit}
                        </span>
                      </div>
                      <div className="h-3 bg-slate-800 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${metric.value}%` }}
                          transition={{ duration: 1, delay: 0.5 + index * 0.1 }}
                          className={`h-full bg-gradient-to-r ${metric.color}`}
                        />
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* Storage & Cleanup */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
            <Database className="w-6 h-6 text-green-400" />
            Storage Management
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                label: "Checkpoints",
                size: systemInfo?.checkpoints_size || 0,
                icon: Folder,
                color: "from-cyan-500 to-blue-500",
                action: "checkpoints" as const,
                description: "Saved project states",
              },
              {
                label: "Generated Apps",
                size: systemInfo?.generated_apps_size || 0,
                icon: Code,
                color: "from-purple-500 to-pink-500",
                action: "generated" as const,
                description: "Generated code repositories",
              },
              {
                label: "Total Project Data",
                size: (systemInfo?.checkpoints_size || 0) + (systemInfo?.generated_apps_size || 0),
                icon: Database,
                color: "from-green-500 to-emerald-500",
                action: "all" as const,
                description: "All project-related files",
              },
            ].map((storage, index) => {
              const Icon = storage.icon;
              return (
                <GlassCard key={storage.label} className="p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`p-3 rounded-xl bg-gradient-to-br ${storage.color}`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white">{storage.label}</h3>
                      <p className="text-xs text-slate-400">{storage.description}</p>
                    </div>
                  </div>
                  <div className="text-3xl font-bold text-white mb-4">
                    {storage.size.toFixed(1)} GB
                  </div>
                  <GradientButton
                    variant="secondary"
                    onClick={() => cleanupMutation.mutate(storage.action)}
                    disabled={cleanupMutation.isPending}
                    className="w-full justify-center"
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    {cleanupMutation.isPending ? "Cleaning..." : "Cleanup"}
                  </GradientButton>
                </GlassCard>
              );
            })}
          </div>
        </motion.div>

        {/* Info Banner */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          className="mt-12"
        >
          <GlassCard className="p-6 border-blue-500/30 bg-blue-500/5">
            <div className="flex items-start gap-4">
              <Info className="w-6 h-6 text-blue-400 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-white mb-2">System Information</h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  The AI Website Builder runs entirely on your local machine using Ollama. 
                  All generation, processing, and data storage happens locally. 
                  For best performance, ensure you have at least 16GB RAM and the required models are downloaded.
                </p>
              </div>
            </div>
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
}
