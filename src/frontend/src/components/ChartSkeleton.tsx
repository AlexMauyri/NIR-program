import './ChartSkeleton.css';

/** Заглушка на время первичной загрузки графика — сохраняет высоту, чтобы не было прыжка layout. */
export function ChartSkeleton() {
  return (
    <div className="chart-skeleton" role="status" aria-label="Загрузка графика">
      <div className="chart-skeleton__bars">
        {Array.from({ length: 12 }).map((_, i) => (
          <div
            key={i}
            className="chart-skeleton__bar"
            style={{ height: `${30 + ((i * 37) % 60)}%` }}
          />
        ))}
      </div>
    </div>
  );
}
