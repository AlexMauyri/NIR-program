import { httpClient } from "./httpClient";

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
