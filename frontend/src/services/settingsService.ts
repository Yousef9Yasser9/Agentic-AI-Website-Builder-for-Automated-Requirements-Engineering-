import { api } from "./api";
import type { ModelSettings, OllamaStatus, SizeReport } from "../types/project";

export async function getModelSettings() {
  const { data } = await api.get<ModelSettings>("/api/settings/models");
  return data;
}

export async function updateModelSettings(payload: ModelSettings) {
  const { data } = await api.put<ModelSettings>("/api/settings/models", payload);
  return data;
}

export async function getOllamaStatus() {
  const { data } = await api.get<OllamaStatus>("/api/ollama/status");
  return data;
}

export async function getSizeReport() {
  const { data } = await api.get<SizeReport>("/api/system/size-report");
  return data;
}

export async function cleanupSystem(payload: { keep_apps: number; keep_checkpoints: number }) {
  const { data } = await api.post("/api/system/cleanup", payload);
  return data;
}

