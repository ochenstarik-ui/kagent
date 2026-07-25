const foundationItems = [
  "Версионируемые контракты",
  "Control Plane",
  "Security Gateway",
  "PostgreSQL",
  "NATS JetStream",
  "S3-совместимые артефакты"
] as const;

export default function HomePage() {
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">KAGENT · 0.1.0-DEV</p>
        <h1>Автономная инженерная система с проверяемыми результатами</h1>
        <p className="lead">
          Первый инкремент закладывает независимое ядро платформы, прозрачные
          контракты и безопасные границы выполнения.
        </p>
      </section>

      <section className="panel">
        <div>
          <p className="label">Текущий этап</p>
          <h2>Foundation Bootstrap</h2>
        </div>
        <span className="status">В разработке</span>
      </section>

      <section className="grid" aria-label="Компоненты основания">
        {foundationItems.map((item, index) => (
          <article key={item}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <h3>{item}</h3>
          </article>
        ))}
      </section>
    </main>
  );
}
