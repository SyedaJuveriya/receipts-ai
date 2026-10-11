
import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "Just now";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function App() {
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("project");
  const [searchInput, setSearchInput] = useState("project");
  const [memories, setMemories] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activities, setActivities] = useState([
    {
      title: "Memory engine initialized",
      detail: "Ready to retrieve and process memories.",
      time: new Date().toISOString(),
      type: "system",
    },
  ]);
  const [lastResult, setLastResult] = useState(null);

  const addActivity = useCallback((title, detail, type = "system") => {
    setActivities((previous) => [
      {
        title,
        detail,
        time: new Date().toISOString(),
        type,
      },
      ...previous,
    ].slice(0, 8));
  }, []);

  const searchMemories = useCallback(async (searchTerm = query) => {
    setSearching(true);
    setError("");

    try {
      const params = new URLSearchParams({
        q: searchTerm.trim() || "project",
        limit: "20",
      });

      const response = await fetch(`${API}/memories/search?${params}`);

      if (!response.ok) {
        throw new Error(`Memory search failed (${response.status})`);
      }

      const data = await response.json();
      setMemories(data.results || []);
      addActivity(
        "Memory retrieval completed",
        `${(data.results || []).length} matching memories returned by Qdrant.`,
        "retrieval",
      );
    } catch (err) {
      setError(
        "Couldn't reach the backend. Make sure FastAPI is running at 127.0.0.1:8000.",
      );
      addActivity("Retrieval failed", err.message, "error");
    } finally {
      setSearching(false);
    }
  }, [query, addActivity]);

  useEffect(() => {
    searchMemories("project");
  }, []); // Initial load only.

  async function handleCapture(event) {
    event.preventDefault();

    if (!message.trim() || loading) return;

    setLoading(true);
    setError("");
    setNotice("");
    setLastResult(null);

    addActivity("Capture received", "Sending your message to the Lyzr extraction agent.", "capture");

    try {
      const response = await fetch(`${API}/memories/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim() }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `Request failed (${response.status})`);
      }

      setLastResult(data);
      setNotice(
        `Processed ${data.extracted_count ?? 0} extracted memories. Saved ${data.saved_count ?? 0}, detected ${data.duplicate_count ?? 0} duplicates.`,
      );

      addActivity(
        "Extraction completed",
        `${data.extracted_count ?? 0} extracted · ${data.saved_count ?? 0} saved · ${data.duplicate_count ?? 0} duplicates.`,
        "success",
      );

      if ((data.superseded_count ?? 0) > 0) {
        addActivity(
          "Previous decision superseded",
          `${data.superseded_count} previous decision(s) marked as superseded.`,
          "update",
        );
      }

      if ((data.review_required_count ?? 0) > 0) {
        addActivity(
          "Review required",
          `${data.review_required_count} memory item(s) need review.`,
          "review",
        );
      }

      setMessage("");
      await searchMemories(query);
    } catch (err) {
      setError(err.message || "Could not process this message.");
      addActivity("Capture failed", err.message, "error");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(event) {
    event.preventDefault();
    const nextQuery = searchInput.trim() || "project";
    setQuery(nextQuery);
    await searchMemories(nextQuery);
  }

  const filteredMemories = useMemo(() => {
    if (filter === "ALL") return memories;
    if (filter === "ACTIVE") {
      return memories.filter((item) => item.status === "ACTIVE");
    }
    if (filter === "SUPERSEDED") {
      return memories.filter((item) => item.status === "SUPERSEDED");
    }
    return memories.filter((item) => item.memory_type === filter);
  }, [memories, filter]);

  const stats = useMemo(() => ({
    total: memories.length,
    decisions: memories.filter((item) => item.memory_type === "DECISION").length,
    commitments: memories.filter((item) => item.memory_type === "COMMITMENT").length,
    superseded: memories.filter((item) => item.status === "SUPERSEDED").length,
  }), [memories]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Receipts home">
          <span className="brand-mark">R<span>.</span></span>
          <span className="brand-copy">
            <strong>RECEIPTS</strong>
            <small>Persistent memory</small>
          </span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-item active" href="#overview"><span>◈</span> Overview</a>
          <a className="nav-item" href="#capture"><span>＋</span> Capture memory</a>
          <a className="nav-item" href="#memories"><span>▤</span> Memory explorer</a>
          <a className="nav-item" href="#activity"><span>⌁</span> Agent activity</a>
        </nav>

        <div className="sidebar-bottom">
          <div className="connection-card">
            <span className="connection-dot" />
            <div>
              <strong>Local environment</strong>
              <small>FastAPI · Qdrant</small>
            </div>
          </div>
          <div className="sidebar-footer">
            <span>RECEIPTS AI</span>
            <span>v0.1.0</span>
          </div>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> Overview</div>
          <div className="topbar-right">
            <span className="live-pill"><span /> MEMORY ENGINE</span>
            <div className="avatar">R</div>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> YOUR CONTEXT, PRESERVED</div>
              <h1>Memory that <span>moves with you.</span></h1>
              <p className="welcome-copy">
                Capture what you said, retrieve what matters, and keep decisions connected as things change.
              </p>
            </div>
            <div className="date-chip">◷ &nbsp; Persistent memory workspace</div>
          </section>

          {error && <div className="alert error-alert"><strong>Connection issue</strong><span>{error}</span></div>}
          {notice && <div className="alert success-alert"><strong>Capture processed</strong><span>{notice}</span></div>}

          <section className="stats-grid">
            <StatCard label="MATCHING MEMORIES" value={stats.total} foot="In current search results" icon="▤" tone="purple" />
            <StatCard label="DECISIONS" value={stats.decisions} foot="Choices and changes" icon="◇" tone="blue" />
            <StatCard label="COMMITMENTS" value={stats.commitments} foot="Actions to follow through" icon="↗" tone="orange" />
            <StatCard label="SUPERSEDED" value={stats.superseded} foot="Replaced in these results" icon="⟳" tone="green" />
          </section>

          <section className="capture-panel" id="capture">
            <div className="capture-heading">
              <div className="capture-icon">✳</div>
              <div>
                <div className="section-kicker">MEMORY INTAKE</div>
                <h2>What should I remember?</h2>
                <p>Write naturally. RECEIPTS extracts decisions, commitments, and useful notes.</p>
              </div>
              <span className="powered-label">POWERED BY LYZR</span>
            </div>

            <form onSubmit={handleCapture}>
              <label className="sr-only" htmlFor="memory-input">Your message</label>
              <textarea
                id="memory-input"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder={'“We decided to use PostgreSQL. I’ll submit the architecture diagram tomorrow.”'}
                maxLength={5000}
                rows={3}
              />
              <div className="capture-bottom">
                <span className="input-hint">↳ &nbsp; Commitments · Decisions · Changes</span>
                <div className="capture-actions">
                  <span className="character-count">{message.length}/5000</span>
                  <button className="primary-button" type="submit" disabled={loading || !message.trim()}>
                    {loading ? <><span className="spinner" /> Processing…</> : <>Process memory <span>↗</span></>}
                  </button>
                </div>
              </div>
            </form>

            {lastResult && (
              <div className="result-strip">
                <ResultMetric label="Extracted" value={lastResult.extracted_count ?? 0} />
                <ResultMetric label="Saved" value={lastResult.saved_count ?? 0} />
                <ResultMetric label="Duplicates" value={lastResult.duplicate_count ?? 0} />
                <ResultMetric label="Superseded" value={lastResult.superseded_count ?? 0} />
              </div>
            )}
          </section>

          <div className="content-grid">
            <section className="panel memory-panel" id="memories">
              <div className="panel-heading">
                <div>
                  <div className="section-kicker">YOUR KNOWLEDGE BASE</div>
                  <h2>Memory explorer</h2>
                  <p>Search meaning, not just exact words.</p>
                </div>
                <span className="count-badge">{filteredMemories.length} results</span>
              </div>

              <form className="search-form" onSubmit={handleSearch}>
                <span className="search-icon">⌕</span>
                <input
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search your memories…"
                  aria-label="Search memories"
                />
                <button type="submit" disabled={searching}>{searching ? "Searching…" : "Search"}</button>
              </form>

              <div className="filter-row">
                {["ALL", "DECISION", "COMMITMENT", "NOTE", "ACTIVE", "SUPERSEDED"].map((item) => (
                  <button
                    key={item}
                    type="button"
                    className={`filter-chip ${filter === item ? "selected" : ""}`}
                    onClick={() => setFilter(item)}
                  >
                    {item === "ALL" ? "All" : item.charAt(0) + item.slice(1).toLowerCase().replace("_", " ")}
                  </button>
                ))}
              </div>

              <div className="memory-list">
                {filteredMemories.map((memory) => (
                  <article className="memory-item" key={memory.id}>
                    <div className={`memory-type-icon ${String(memory.memory_type).toLowerCase()}`}>
                      {memory.memory_type === "DECISION" ? "◇" : memory.memory_type === "COMMITMENT" ? "↗" : "≡"}
                    </div>
                    <div className="memory-body">
                      <div className="memory-meta">
                        <span className={`type-label ${String(memory.memory_type).toLowerCase()}`}>{memory.memory_type}</span>
                        <span className="memory-time">{formatDate(memory.created_at)}</span>
                      </div>
                      <p>{memory.content}</p>
                      <div className="memory-bottom">
                        <span className={`status-pill ${String(memory.status || "ACTIVE").toLowerCase()}`}>
                          <span /> {String(memory.status || "ACTIVE").replace("_", " ")}
                        </span>
                        {memory.relationship && memory.relationship !== "NEW" && (
                          <span className="relationship-label">{memory.relationship}</span>
                        )}
                      </div>
                    </div>
                    <div className="similarity">
                      <strong>{typeof memory.score === "number" ? `${Math.round(memory.score * 100)}%` : "—"}</strong>
                      <small>match</small>
                    </div>
                  </article>
                ))}

                {!searching && filteredMemories.length === 0 && (
                  <div className="empty-state">
                    <span>⌕</span>
                    <strong>No matching memories</strong>
                    <p>Try another search or capture a new memory above.</p>
                  </div>
                )}
                {searching && <div className="loading-state"><span className="spinner" /> Retrieving memories…</div>}
              </div>

              <div className="panel-footer">
                <span>Semantic retrieval by Qdrant</span>
                <button type="button" onClick={() => searchMemories(query)}>↻ Refresh results</button>
              </div>
            </section>

            <div className="right-column">
              <section className="panel workflow-panel">
                <div className="panel-heading">
                  <div>
                    <div className="section-kicker">HOW IT WORKS</div>
                    <h2>Agent workflow</h2>
                  </div>
                  <span className="workflow-indicator"><span /> READY</span>
                </div>
                <div className="workflow-list">
                  <WorkflowStep number="01" title="Capture" detail="Receive your natural-language input" />
                  <WorkflowStep number="02" title="Extract" detail="Lyzr identifies memory candidates" />
                  <WorkflowStep number="03" title="Retrieve" detail="Qdrant finds related context" />
                  <WorkflowStep number="04" title="Evaluate" detail="Check duplicates and decision changes" />
                  <WorkflowStep number="05" title="Persist" detail="Save memory and relationship metadata" last />
                </div>
                <div className="workflow-note">
                  <span>✳</span>
                  <p><strong>Context over chat history.</strong><br />Memories remain searchable after the request ends.</p>
                </div>
              </section>

              <section className="panel activity-panel" id="activity">
                <div className="panel-heading">
                  <div>
                    <div className="section-kicker">SYSTEM TRACE</div>
                    <h2>Agent activity</h2>
                  </div>
                  <span className="activity-count">{activities.length}</span>
                </div>
                <div className="activity-list">
                  {activities.map((activity, index) => (
                    <div className="activity-item" key={`${activity.time}-${index}`}>
                      <div className={`activity-marker ${activity.type}`} />
                      <div className="activity-copy">
                        <strong>{activity.title}</strong>
                        <p>{activity.detail}</p>
                        <small>{formatDate(activity.time)}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          </div>

          <footer className="page-footer">
            <span>RECEIPTS <span className="footer-dot">●</span> PERSISTENT MEMORY FOR REAL LIFE</span>
            <span>Built with FastAPI · Qdrant · Lyzr</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

function StatCard({ label, value, foot, icon, tone }) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className={`stat-icon ${tone}`}>{icon}</span>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-foot"><span />{foot}</div>
    </article>
  );
}

function ResultMetric({ label, value }) {
  return <div className="result-metric"><strong>{value}</strong><span>{label}</span></div>;
}

function WorkflowStep({ number, title, detail, last }) {
  return (
    <div className={`workflow-step ${last ? "last" : ""}`}>
      <div className="step-number">{number}</div>
      <div className="step-copy"><strong>{title}</strong><small>{detail}</small></div>
      <span className="step-check">✓</span>
    </div>
  );
}

export default App;
