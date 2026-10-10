import { httpClient } from "./httpClient";
import type { PredictionRequest, PredictionResponse } from "../types/predictions";

export async function getPredictions(req: PredictionRequest): Promise<PredictionResponse> {
  const { data } = await httpClient.post<PredictionResponse>("/predict/", req);
  return data;
}
