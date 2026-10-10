export interface PredictionRequest {
  model_name: string;
  start_date: string; // YYYY-MM-DD
  end_date: string;   // YYYY-MM-DD
}

export interface PredictionResponse {
  dates: string[];
  predictions: number[];
  model_name: string;
}
