export interface WindowedIndicatorSettings {
  enabled: boolean;
  period: number;
}

export interface BollingerIndicatorSettings extends WindowedIndicatorSettings {
  stdDevMultiplier: number;
}

export interface MacdIndicatorSettings {
  enabled: boolean;
  fastPeriod: number;
  slowPeriod: number;
  signalPeriod: number;
}

export interface IndicatorSettings {
  sma: WindowedIndicatorSettings;
  ema: WindowedIndicatorSettings;
  bollinger: BollingerIndicatorSettings;
  rsi: WindowedIndicatorSettings;
  macd: MacdIndicatorSettings;
}

export const DEFAULT_INDICATOR_SETTINGS: IndicatorSettings = {
  sma: { enabled: false, period: 20 },
  ema: { enabled: false, period: 20 },
  bollinger: { enabled: false, period: 20, stdDevMultiplier: 2 },
  rsi: { enabled: false, period: 14 },
  macd: { enabled: false, fastPeriod: 12, slowPeriod: 26, signalPeriod: 9 },
};
