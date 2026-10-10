import type { IndicatorSettings } from '../types/indicators';
import './IndicatorSelector.css';

interface IndicatorSelectorProps {
  settings: IndicatorSettings;
  onChange: (next: IndicatorSettings) => void;
}

function sanitizePeriod(raw: string, min = 2, max = 200): number | null {
  const value = Number(raw);
  if (!Number.isFinite(value)) return null;
  return Math.min(max, Math.max(min, Math.round(value)));
}

export function IndicatorSelector({ settings, onChange }: IndicatorSelectorProps) {
  const toggleSma = () =>
    onChange({ ...settings, sma: { ...settings.sma, enabled: !settings.sma.enabled } });
  const toggleEma = () =>
    onChange({ ...settings, ema: { ...settings.ema, enabled: !settings.ema.enabled } });
  const toggleBollinger = () =>
    onChange({
      ...settings,
      bollinger: { ...settings.bollinger, enabled: !settings.bollinger.enabled },
    });
  const toggleRsi = () =>
    onChange({ ...settings, rsi: { ...settings.rsi, enabled: !settings.rsi.enabled } });
  const toggleMacd = () =>
    onChange({ ...settings, macd: { ...settings.macd, enabled: !settings.macd.enabled } });

  const handlePeriodChange = (
    key: 'sma' | 'ema' | 'bollinger' | 'rsi',
    raw: string,
  ) => {
    const period = sanitizePeriod(raw);
    if (period == null) return;
    onChange({ ...settings, [key]: { ...settings[key], period } });
  };

  return (
    <div className="indicator-selector">
      <span className="indicator-selector__title">Индикаторы</span>

      <div className="indicator-selector__item">
        <label className="indicator-selector__label">
          <input type="checkbox" checked={settings.sma.enabled} onChange={toggleSma} />
          SMA
        </label>
        <input
          type="number"
          className="indicator-selector__period"
          min={2}
          max={200}
          value={settings.sma.period}
          disabled={!settings.sma.enabled}
          onChange={(e) => handlePeriodChange('sma', e.target.value)}
          aria-label="Окно SMA"
        />
      </div>

      <div className="indicator-selector__item">
        <label className="indicator-selector__label">
          <input type="checkbox" checked={settings.ema.enabled} onChange={toggleEma} />
          EMA
        </label>
        <input
          type="number"
          className="indicator-selector__period"
          min={2}
          max={200}
          value={settings.ema.period}
          disabled={!settings.ema.enabled}
          onChange={(e) => handlePeriodChange('ema', e.target.value)}
          aria-label="Окно EMA"
        />
      </div>

      <div className="indicator-selector__item">
        <label className="indicator-selector__label">
          <input
            type="checkbox"
            checked={settings.bollinger.enabled}
            onChange={toggleBollinger}
          />
          Полосы Боллинджера
        </label>
        <input
          type="number"
          className="indicator-selector__period"
          min={2}
          max={200}
          value={settings.bollinger.period}
          disabled={!settings.bollinger.enabled}
          onChange={(e) => handlePeriodChange('bollinger', e.target.value)}
          aria-label="Окно полос Боллинджера"
        />
      </div>

      <div className="indicator-selector__item">
        <label className="indicator-selector__label">
          <input type="checkbox" checked={settings.rsi.enabled} onChange={toggleRsi} />
          RSI
        </label>
        <input
          type="number"
          className="indicator-selector__period"
          min={2}
          max={200}
          value={settings.rsi.period}
          disabled={!settings.rsi.enabled}
          onChange={(e) => handlePeriodChange('rsi', e.target.value)}
          aria-label="Окно RSI"
        />
      </div>

      <div className="indicator-selector__item">
        <label className="indicator-selector__label">
          <input type="checkbox" checked={settings.macd.enabled} onChange={toggleMacd} />
          MACD (12/26/9)
        </label>
      </div>
    </div>
  );
}
