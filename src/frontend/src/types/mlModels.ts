export interface ModelVersionMetrics {
  version: number;
  aliases: string[];
  created_at: string; // ISO
  metrics: Record<string, number>;
  params: Record<string, string>;
}

export interface ModelMetrics {
  model_name: string;
  versions: ModelVersionMetrics[];
}

export interface AllModelsMetrics {
  models: Record<string, ModelMetrics>;
}
