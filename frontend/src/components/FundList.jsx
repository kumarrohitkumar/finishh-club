/**
 * FUND LIST - browse and search.
 *
 * Deliberately calm: name, house, category. No returns, no ratings, no red and
 * green numbers. PRD section 2 - the problem being solved is that every other
 * finance screen opens with moving numbers a beginner cannot read.
 */
import { useEffect, useState } from "react";
import { listFunds } from "../api";

const CATEGORIES = [
  { value: "", label: "All" },
  { value: "equity", label: "Equity" },
  { value: "hybrid", label: "Hybrid" },
  { value: "debt", label: "Debt" },
];

function Skeletons() {
  return (
    <ul className="funds">
      {[0, 1, 2, 3].map((i) => (
        <li key={i}><div className="fund-card skeleton-card">
          <div className="skeleton skeleton-line w60" />
          <div className="skeleton skeleton-line w40" />
        </div></li>
      ))}
    </ul>
  );
}

export default function FundList({ onOpen }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    const id = setTimeout(() => {
      listFunds({ q, category })
        .then((d) => { setItems(d.items); setTotal(d.total); setError(""); })
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(id);
  }, [q, category]);

  return (
    <div className="list">
      <section className="hero">
        <h1>Understand a fund<br />before you decide.</h1>
        <p className="lede">
          Plain English explanations, the full history of outcomes, and an
          assistant that answers questions — without ever telling you what to buy.
        </p>
      </section>

      <div className="controls">
        <div className="search">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" strokeWidth="1.8" />
            <line x1="13.5" y1="13.5" x2="18" y2="18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
          </svg>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search funds"
            aria-label="Search funds"
          />
        </div>
        <div className="filters">
          {CATEGORIES.map((c) => (
            <button
              key={c.value || "all"}
              className={c.value === category ? "chip on" : "chip"}
              onClick={() => setCategory(c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {loading ? <Skeletons /> : (
        <>
          <p className="count">{total} {total === 1 ? "fund" : "funds"}</p>
          {items.length === 0 ? (
            <div className="empty">
              <p>No funds match “{q}”.</p>
              <button className="chip" onClick={() => { setQ(""); setCategory(""); }}>
                Clear filters
              </button>
            </div>
          ) : (
            <ul className="funds">
              {items.map((fund) => (
                <li key={fund.source_code}>
                  <button className="fund-card" onClick={() => onOpen(fund.source_code)}>
                    <span className="fund-top">
                      <span className="fund-name">{fund.name}</span>
                      <span className={`tag ${fund.category}`}>{fund.category}</span>
                    </span>
                    <span className="fund-house">{fund.fund_house}</span>
                    <span className="fund-go" aria-hidden="true">→</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
