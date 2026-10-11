import { httpClient } from "./httpClient";
import type { PredictionRequest, PredictionResponse } from "../types/predictions";

export async function getPredictions(
  req: PredictionRequest,
  signal?: AbortSignal,
): Promise<PredictionResponse> {
  const { data } = await httpClient.post<PredictionResponse>("/predict/", req, { signal });
  return data;
}
