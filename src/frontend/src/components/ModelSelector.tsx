import type { ModelInfo } from "../api/mlModels";
import "./ModelSelector.css";

interface Props {
  models: ModelInfo[];
  selected: string | null;
  onChange: (name: string) => void;
  disabled?: boolean;
}

export default function ModelSelector({ models, selected, onChange, disabled }: Props) {
  return (
    <select
      className="model-selector"
      value={selected ?? ""}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled || models.length === 0}
    >
      <option value="" disabled>Выберите модель</option>
      {models.map((m) => (
        <option key={m.name} value={m.name}>{m.name}</option>
      ))}
    </select>
  );
}
