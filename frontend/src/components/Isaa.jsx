/**
 * ISAA - the assistant panel.
 *
 * WHY MARKDOWN IS RENDERED
 *   Isaa answers about a meter across three holding periods are genuinely a
 *   table. Shown as raw text the reader gets a wall of pipes and dashes.
 *
 * WHY react-markdown AND NOT dangerouslySetInnerHTML
 *   This is model output being put on a page. react-markdown escapes HTML by
 *   default, so a model that emitted a <script> tag would render it as text.
 *   rehype-raw would switch that protection off - we do not use it.
 *
 * WHY THE TOOLS USED ARE SHOWN
 *   Isaa's answers contain numbers. Showing which tools produced them lets a
 *   person see the answer came from our data rather than the model's memory.
 *   It is the visible half of eval E-2.
 *
 * WHY FAILURE IS QUIET
 *   Isaa is not on the critical path (HLD section 8). If the model is down, the
 *   fund page and the meter must keep working - so an error is a small message
 *   inside this panel, never a broken page.
 */
import { useEffect, useRef, useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { askIsaa } from "../api";

const SUGGESTIONS = [
  "Is this fund risky?",
  "What does the meter mean?",
  "What is an expense ratio?",
];

export default function Isaa({ fundCode, fundName }) {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState([]);
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); },
            [turns, busy]);

  async function send(text) {
    const asked = (text ?? question).trim();
    if (!asked || busy) return;
    setQuestion("");
    setBusy(true);
    setTurns((t) => [...t, { role: "user", text: asked }]);
    try {
      const reply = await askIsaa(asked, fundCode);
      setTurns((t) => [...t, { role: "isaa", text: reply.answer, tools: reply.tools_used }]);
    } catch (e) {
      setTurns((t) => [...t, { role: "error", text: e.message, retry: asked }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card isaa">
      <div className="isaa-head">
        <span className="isaa-dot" aria-hidden="true" />
        <h2>Ask Isaa</h2>
      </div>
      <p className="isaa-sub">
        {fundName ? "Ask anything about this fund. " : ""}
        Isaa explains — it never tells you what to buy.
      </p>

      {turns.length > 0 && (
        <div className="turns">
          {turns.map((turn, i) => (
            <div key={i} className={`turn ${turn.role}`}>
              {turn.role === "isaa" ? (
                <div className="md">
                  <Markdown remarkPlugins={[remarkGfm]}>{turn.text}</Markdown>
                </div>
              ) : (
                <p>{turn.text}</p>
              )}
              {turn.role === "error" && turn.retry && (
                <button className="retry" onClick={() => send(turn.retry)}>
                  Try again
                </button>
              )}
              {turn.tools?.length > 0 && (
                <p className="tools">
                  Looked up: {turn.tools.map((t) => t.tool.replace(/_/g, " ")).join(" · ")}
                </p>
              )}
            </div>
          ))}
          {busy && (
            <div className="turn isaa thinking">
              <p>Isaa is looking it up<span className="ellipsis" /></p>
            </div>
          )}
          <div ref={endRef} />
        </div>
      )}

      {turns.length === 0 && (
        <div className="suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <form className="ask" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question…"
          maxLength={500}
          aria-label="Ask Isaa a question"
        />
        <button type="submit" disabled={busy || !question.trim()}>Ask</button>
      </form>
    </section>
  );
}
