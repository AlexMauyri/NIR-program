import { httpClient } from "./httpClient";
import type { AllModelsMetrics } from "../types/mlModels";

export interface ModelInfo {
  name: string;
  version: string;
  alias: string;
  metrics: Record<string, number>;
}

export async function getModels(): Promise<ModelInfo[]> {
  const { data } = await httpClient.get<ModelInfo[]>("/ml-models");
  return data;
}

export async function getAllModelMetrics(): Promise<AllModelsMetrics> {
  const { data } = await httpClient.get<AllModelsMetrics>("/ml-models/metrics");
  return data;
}
