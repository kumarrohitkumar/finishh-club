/**
 * FUND DETAIL PAGE - the order of things here is a product rule, not a layout
 * preference.
 *
 * PRD rule F-1, top to bottom:
 *   1. name, house, category        visible
 *   2. the Finishh Meter            visible
 *   3. Isaa                         visible
 *   4. everything else              COLLAPSED
 *
 * "Answer before data" (PRD section 3 rule 1) - a beginner must meet an
 * explanation before a wall of numbers. Rule F-3: nothing renders a chart until
 * a person opens it.
 *
 * Rule F-6: a value we do not hold reads "Not available". Never blank, never
 * zero - a zero NAV would look like a total loss.
 */
import { useEffect, useState } from "react";
import { getFund, getMeter } from "../api";
import Meter from "./Meter";
import Isaa from "./Isaa";

const show = (v) => (v === null || v === undefined ? "Not available" : v);

export default function FundDetail({ code, onBack }) {
  const [fund, setFund] = useState(null);
  const [meter, setMeter] = useState(null);
  const [period, setPeriod] = useState(3);
  const [loadingMeter, setLoadingMeter] = useState(true);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getFund(code).then(setFund).catch((e) => setError(e.message));
  }, [code]);

  useEffect(() => {
    setLoadingMeter(true);
    getMeter(code, period)
      .then(setMeter).catch(() => setMeter(null))
      .finally(() => setLoadingMeter(false));
  }, [code, period]);

  if (error) return <p className="error">{error}</p>;

  if (!fund) {
    return (
      <div className="detail">
        <div className="card">
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-line w40" />
        </div>
      </div>
    );
  }

  return (
    <div className="detail">
      <button className="back" onClick={onBack}>← All funds</button>

      <header className="card detail-head">
        <h1>{fund.name}</h1>
        <p className="fund-house">{fund.fund_house}</p>
        <div className="tags">
          <span className={`tag ${fund.category}`}>{fund.category}</span>
          <span className="tag">{fund.sub_category}</span>
        </div>
      </header>

      <Meter meter={meter} period={period} onPeriodChange={setPeriod} loading={loadingMeter} />

      <Isaa fundCode={code} fundName={fund.name} />

      {/* Rules F-1 and F-3: everything below starts closed */}
      <section className="card">
        <button className={open ? "reveal open" : "reveal"} onClick={() => setOpen(!open)}>
          <span>{open ? "Hide details" : "View details"}</span>
          <span className="caret" aria-hidden="true">⌄</span>
        </button>

        {open && (
          <dl className="facts">
            <div><dt>Latest NAV</dt><dd>{show(fund.latest_nav)}</dd></div>
            <div><dt>As of</dt><dd>{show(fund.latest_nav_date)}</dd></div>
            <div><dt>History from</dt><dd>{show(fund.history_from)}</dd></div>
            <div><dt>Price points</dt><dd>{fund.price_points.toLocaleString()}</dd></div>
            <div><dt>Scheme code</dt><dd>{fund.source_code}</dd></div>
            <div><dt>Source</dt><dd>{fund.source}</dd></div>
          </dl>
        )}
      </section>
    </div>
  );
}
