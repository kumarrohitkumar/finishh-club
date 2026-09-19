/**
 * APP - shell, brand bar, and the two screens.
 *
 * No router yet on purpose. One piece of state decides which screen shows.
 * React Router goes in when there is a third screen and shareable URLs matter.
 */
import { useState } from "react";
import FundList from "./components/FundList";
import FundDetail from "./components/FundDetail";
import "./App.css";

export default function App() {
  const [code, setCode] = useState(null);

  return (
    <div className="shell">
      <nav className="topbar">
        <button className="brand" onClick={() => setCode(null)}>
          <span className="mark" aria-hidden="true" />
          Finishh<span className="brand-light">club</span>
        </button>
        <span className="badge">Mutual funds</span>
      </nav>

      <main className="app">
        {code
          ? <FundDetail code={code} onBack={() => setCode(null)} />
          : <FundList onOpen={setCode} />}
      </main>

      <footer className="site-foot">
        <p>Fund data from AMFI. Updated daily.</p>
        <p>Finishh club explains funds. It does not give investment advice.</p>
      </footer>
    </div>
  );
}
