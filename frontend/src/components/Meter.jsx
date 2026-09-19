/**
 * THE FINISHH METER - the product's signature feature.
 *
 * WHY ONE STACKED BAR AND NOT FOUR SEPARATE ONES
 *   The four numbers are parts of a single whole that always totals 100%. Four
 *   separate bars invite the eye to compare them against nothing. One bar split
 *   into four shows what the data actually is: every past period, sorted.
 *
 * THREE PRODUCT RULES LIVE HERE
 *   M-6  the scale in use is ALWAYS on screen. Without it a user compares a
 *        debt meter to an equity meter and concludes wrongly.
 *   M-5  a fund too young for the period falls back and says so. Never an
 *        empty bar.
 *   6.5  wording: "of past periods", never "chance".
 */
const COLOURS = {
  green: "#2f7d52",
  orange: "#c98a2e",
  blue: "#4a7fd4",
  red: "#c2483c",
};

const PERIODS = [1, 3, 5];

export default function Meter({ meter, period, onPeriodChange, loading }) {
  if (loading) {
    return (
      <section className="card meter">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-bar" />
        <div className="skeleton skeleton-line" />
      </section>
    );
  }
  if (!meter) return null;

  const fellBack = meter.shown_period_years !== meter.requested_period_years;
  const headline = meter.buckets.find((b) => b.key === "strong");
  const loss = meter.buckets.find((b) => b.key === "loss");

  return (
    <section className="card meter">
      <header className="meter-head">
        <div>
          <p className="eyebrow">Finishh Meter</p>
          <h2>If you had held this fund for {meter.shown_period_years} year
            {meter.shown_period_years > 1 ? "s" : ""}…</h2>
        </div>
        <div className="segmented" role="group" aria-label="Holding period">
          {PERIODS.map((years) => (
            <button
              key={years}
              className={years === period ? "seg on" : "seg"}
              onClick={() => onPeriodChange(years)}
            >
              {years}Y
            </button>
          ))}
        </div>
      </header>

      {meter.insufficient_history ? (
        <p className="note">{meter.note}</p>
      ) : (
        <>
          {/* Answer before data - PRD section 3 rule 1 */}
          <p className="headline">
            <strong>{headline.percent.toFixed(0)}%</strong> of past
            {" "}{meter.shown_period_years}-year periods returned more than 10% a year.
            {loss.percent > 0 && (
              <> <strong>{loss.percent.toFixed(1)}%</strong> ended in a loss.</>
            )}
          </p>

          {fellBack && <p className="note">{meter.note}</p>}

          <div className="stack" role="img"
               aria-label={meter.buckets.map((b) => `${b.label}: ${b.percent}%`).join(", ")}>
            {meter.buckets.filter((b) => b.percent > 0).map((b) => (
              <span
                key={b.key}
                className="stack-part"
                style={{ width: `${b.percent}%`, background: COLOURS[b.colour] }}
                title={`${b.label} — ${b.percent}%`}
              />
            ))}
          </div>

          <ul className="legend">
            {meter.buckets.map((b) => (
              <li key={b.key} className={b.percent === 0 ? "off" : ""}>
                <span className="dot" style={{ background: COLOURS[b.colour] }} />
                <span className="legend-label">{b.label}</span>
                <span className="legend-value">{b.percent.toFixed(1)}%</span>
              </li>
            ))}
          </ul>

          {/* Rule M-6 - the meter is never shown without its scale */}
          <footer className="meter-foot">
            <span><b>{meter.window_count.toLocaleString()}</b> periods examined</span>
            <span className="dotsep">·</span>
            <span>{meter.scale} scale</span>
            <span className="dotsep">·</span>
            <span>{meter.data_from} → {meter.data_to}</span>
            <span className="dotsep">·</span>
            <span>{meter.source}</span>
          </footer>
        </>
      )}

      <p className="disclaimer">{meter.disclaimer}</p>
    </section>
  );
}
