import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "Just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function App() {
  const [view, setView] = useState("landing");
  const [message, setMessage] = useState("");
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [memories, setMemories] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [followups, setFollowups] = useState([]);
  const [activities, setActivities] = useState([{ title: "Memory engine initialized", detail: "Ready to retrieve and process memories.", time: new Date().toISOString(), type: "system" }]);

  const addActivity = useCallback((title, detail, type = "system") => {
    setActivities((previous) => [{ title, detail, time: new Date().toISOString(), type }, ...previous].slice(0, 8));
  }, []);

  const searchMemories = useCallback(async (searchTerm = query) => {
    if (!searchTerm.trim()) return;
    setSearching(true);
    setError("");
    try {
      const params = new URLSearchParams({ q: searchTerm.trim(), limit: "20" });
      const response = await fetch(`${API}/memories/search?${params}`);
      if (!response.ok) throw new Error(`Memory search failed (${response.status})`);
      const data = await response.json();
      setMemories(data.results || []);
      addActivity("Memory retrieval completed", `${(data.results || []).length} matching memories returned by Qdrant.`, "retrieval");
    } catch (err) {
      setError("Couldn't reach the backend. Make sure FastAPI is running and the API URL is correct.");
      addActivity("Retrieval failed", err.message, "error");
    } finally { setSearching(false); }
  }, [query, addActivity]);

  const loadFollowups = useCallback(async () => {
    try {
      const response = await fetch(`${API}/memories/followups?limit=5`);
      if (!response.ok) return;
      const data = await response.json();
      setFollowups(data.followups || []);
    } catch { setFollowups([]); }
  }, []);

  useEffect(() => { loadFollowups(); }, [loadFollowups]);

  async function handleCapture(event) {
    event.preventDefault();
    if (!message.trim() || loading) return;
    setLoading(true); setError(""); setNotice(""); setLastResult(null);
    addActivity("Capture received", "Sending your message to the Lyzr extraction agent.", "capture");
    try {
      const response = await fetch(`${API}/memories/extract`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: message.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
      setLastResult(data);
      setNotice(`Processed ${data.extracted_count ?? 0} extracted memories. Saved ${data.saved_count ?? 0}, detected ${data.duplicate_count ?? 0} duplicates.`);
      addActivity("Extraction completed", `${data.extracted_count ?? 0} extracted · ${data.saved_count ?? 0} saved · ${data.duplicate_count ?? 0} duplicates.`, "success");
      if ((data.superseded_count ?? 0) > 0) addActivity("Previous decision superseded", `${data.superseded_count} previous decision(s) marked as superseded.`, "update");
      if ((data.review_required_count ?? 0) > 0) addActivity("Review required", `${data.review_required_count} memory item(s) need review.`, "review");
      setMessage("");
      if (query.trim()) await searchMemories(query);
      await loadFollowups();
    } catch (err) {
      setError(err.message || "Could not process this message.");
      addActivity("Capture failed", err.message, "error");
    } finally { setLoading(false); }
  }

  async function handleSearch(event) {
    event.preventDefault();
    const nextQuery = searchInput.trim();
    if (!nextQuery) return;
    setQuery(nextQuery);
    await searchMemories(nextQuery);
  }

  const filteredMemories = useMemo(() => {
    if (filter === "ALL") return memories;
    if (filter === "ACTIVE") return memories.filter((item) => (item.status || "ACTIVE") === "ACTIVE");
    if (filter === "SUPERSEDED") return memories.filter((item) => item.status === "SUPERSEDED");
    return memories.filter((item) => item.memory_type === filter);
  }, [memories, filter]);
  const stats = useMemo(() => ({
    total: memories.length,
    decisions: memories.filter((item) => item.memory_type === "DECISION").length,
    commitments: memories.filter((item) => item.memory_type === "COMMITMENT").length,
    superseded: memories.filter((item) => item.status === "SUPERSEDED").length,
  }), [memories]);

  function openDashboard() {
    setView("dashboard");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  if (view === "landing") return <Landing onEnter={openDashboard} />;

  return (
    <div className="dashboard-shell">
      <aside className="sidebar glass-panel">
        <button className="brand brand-button" onClick={() => setView("landing")} aria-label="Back to RECEIPTS home">
          <span className="brand-mark">r<span>.</span></span><span className="brand-copy"><strong>RECEIPTS</strong><small>memory, with a paper trail</small></span>
        </button>
        <div className="sidebar-label">YOUR WORKSPACE</div>
        <nav className="side-nav">
          <a className="nav-item active" href="#overview"><span>◫</span> Overview</a>
          <a className="nav-item" href="#capture"><span>＋</span> Capture memory</a>
          <a className="nav-item" href="#memories"><span>⌕</span> Memory explorer</a>
          <a className="nav-item" href="#architecture"><span>⌘</span> Under the hood</a>
          <a className="nav-item" href="#activity"><span>↗</span> Agent activity</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="stack-card"><span className="signal-dot" /><div><strong>Memory engine</strong><small>FastAPI · Lyzr · Qdrant</small></div><span className="stack-orb">✳</span></div>
          <div className="sidebar-footer"><span>RECEIPTS AI</span><span>BUILD 01 / 26</span></div>
        </div>
      </aside>

      <main className="dashboard-main" id="overview">
        <header className="topbar"><div className="crumb">WORKSPACE <span>/</span> MEMORY DESK</div><div className="topbar-actions"><span className="live-pill"><i /> ENGINE READY</span><button className="back-link" onClick={() => setView("landing")}>← Home</button><div className="avatar">R.</div></div></header>
        <div className="dashboard-content">
          <section className="dash-hero">
            <div><div className="eyebrow"><span className="eyebrow-line" /> YOUR CONTEXT, PRESERVED</div><h1>Memory has a<br /><em>paper trail.</em></h1><p>Capture what you said, retrieve what matters, and keep decisions connected as things change.</p></div>
            <div className="hero-stamp"><span>PERSONAL</span><strong>MEMORY<br />LEDGER</strong><small>EST. RIGHT NOW · 001</small></div>
          </section>
          {error && <div className="alert error-alert"><strong>Connection issue</strong><span>{error}</span></div>}
          {notice && <div className="alert success-alert"><strong>Receipt filed</strong><span>{notice}</span></div>}

          <section className="stats-grid">
            <StatCard label="MATCHING MEMORIES" value={stats.total} foot="Current search results" mark="⌕" />
            <StatCard label="DECISIONS" value={stats.decisions} foot="Choices that shape the plan" mark="◇" />
            <StatCard label="COMMITMENTS" value={stats.commitments} foot="Things to follow through" mark="↗" />
            <StatCard label="SUPERSEDED" value={stats.superseded} foot="Updated by newer context" mark="⟳" />
          </section>

          <section className="capture-panel glass-panel" id="capture">
            <div className="capture-heading"><div className="capture-icon">✳</div><div><div className="section-kicker">01 / MEMORY INTAKE</div><h2>Put it on the record.</h2><p>Write like you speak. The agent finds the decisions, commitments, and details worth keeping.</p></div><span className="powered-label">LYZR EXTRACTION</span></div>
            <form onSubmit={handleCapture}>
              <label className="sr-only" htmlFor="memory-input">Your message</label>
              <textarea id="memory-input" value={message} onChange={(event) => setMessage(event.target.value)} placeholder={'“We decided to use PostgreSQL. I’ll send the architecture diagram tomorrow.”'} />
              <div className="capture-bottom"><span className="input-hint">✧ Natural language in. Structured memory out.</span><div className="capture-actions"><span className="character-count">{message.length} characters</span><button className="primary-button" type="submit" disabled={loading || !message.trim()}>{loading ? <><span className="spinner" /> Filing memory…</> : <>File this memory <span>↗</span></>}</button></div></div>
            </form>
            {lastResult && <div className="result-strip"><ResultMetric label="Extracted" value={lastResult.extracted_count ?? 0} /><ResultMetric label="Saved" value={lastResult.saved_count ?? 0} /><ResultMetric label="Duplicates" value={lastResult.duplicate_count ?? 0} /><ResultMetric label="Superseded" value={lastResult.superseded_count ?? 0} /></div>}
          </section>

          <section className="content-grid">
            <section className="panel memory-panel glass-panel" id="memories">
              <div className="panel-heading"><div><div className="section-kicker">02 / YOUR KNOWLEDGE BASE</div><h2>Memory explorer<span className="heading-period">.</span></h2><p>Search meaning, not just exact words.</p></div><span className="count-badge">{filteredMemories.length} found</span></div>
              {followups.length > 0 && <div className="followups"><div className="section-kicker">✳ PROACTIVE FOLLOW-UPS</div><div className="followup-list">{followups.map((item) => <article className="followup-item" key={`fu-${item.id}`}><span className="followup-mark">↗</span><div><div className="memory-meta"><span className={`type-label ${String(item.memory_type).toLowerCase()}`}>{item.memory_type}</span><span className="memory-time">{formatDate(item.created_at)}</span></div><p>{item.nudge}</p></div></article>)}</div></div>}
              <form className="search-form" onSubmit={handleSearch}><span className="search-icon">⌕</span><input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="Try: project deadline, database choice…" aria-label="Search memories" /><button type="submit" disabled={searching}>{searching ? "Searching…" : "Find memory ↗"}</button></form>
              <div className="filter-row">{["ALL", "DECISION", "COMMITMENT", "NOTE", "ACTIVE", "SUPERSEDED"].map((item) => <button key={item} type="button" className={`filter-chip ${filter === item ? "selected" : ""}`} onClick={() => setFilter(item)}>{item === "ALL" ? "Everything" : item.charAt(0) + item.slice(1).toLowerCase().replace("_", " ")}</button>)}</div>
              <div className="memory-list">{filteredMemories.map((memory) => <article className="memory-item" key={memory.id}><div className={`memory-type-icon ${String(memory.memory_type).toLowerCase()}`}>{memory.memory_type === "DECISION" ? "◇" : memory.memory_type === "COMMITMENT" ? "↗" : "≡"}</div><div className="memory-body"><div className="memory-meta"><span className={`type-label ${String(memory.memory_type).toLowerCase()}`}>{memory.memory_type}</span><span className="memory-time">{formatDate(memory.created_at)}</span></div><p>{memory.content}</p><div className="memory-bottom"><span className={`status-pill ${String(memory.status || "ACTIVE").toLowerCase()}`}><span />{String(memory.status || "ACTIVE").replaceAll("_", " ")}</span>{memory.relationship && memory.relationship !== "NEW" && <span className="relationship-label">↳ {memory.relationship}</span>}</div></div><div className="similarity"><strong>{typeof memory.score === "number" ? `${Math.round(memory.score * 100)}%` : "—"}</strong><small>match</small></div></article>)}
                {!searching && filteredMemories.length === 0 && <div className="empty-state"><span>⌕</span><strong>Your ledger starts here.</strong><p>Search for something you’ve captured, or add a memory above.</p></div>}{searching && <div className="loading-state"><span className="spinner" /> Looking through the ledger…</div>}</div>
              <div className="panel-footer"><span>Semantic retrieval · Qdrant</span><button type="button" onClick={() => searchMemories(query)}>↻ Refresh results</button></div>
            </section>

            <div className="right-column">
              <section className="panel workflow-panel glass-panel"><div className="panel-heading"><div><div className="section-kicker">THE ROUTE</div><h2>From words to memory.</h2></div><span className="workflow-indicator"><i /> READY</span></div><div className="workflow-list"><WorkflowStep number="01" title="Capture" detail="Natural language arrives" /><WorkflowStep number="02" title="Extract" detail="Lyzr finds useful memory" /><WorkflowStep number="03" title="Compare" detail="Check for duplicates or changes" /><WorkflowStep number="04" title="Persist" detail="Qdrant keeps it searchable" last /></div><div className="workflow-note"><span>✳</span><p><strong>Not another chat history.</strong><br />A growing record of what matters, even after the conversation ends.</p></div></section>
              <section className="panel activity-panel glass-panel" id="activity"><div className="panel-heading"><div><div className="section-kicker">LIVE PAPER TRAIL</div><h2>Agent activity.</h2></div><span className="activity-count">{activities.length.toString().padStart(2, "0")}</span></div><div className="activity-list">{activities.map((activity, index) => <div className="activity-item" key={`${activity.time}-${index}`}><div className={`activity-marker ${activity.type}`} /><div className="activity-copy"><strong>{activity.title}</strong><p>{activity.detail}</p><small>{formatDate(activity.time)}</small></div></div>)}</div></section>
            </div>
          </section>

          <ArchitectureDiagram />
          <footer className="page-footer"><span>RECEIPTS <b>✳</b> PERSISTENT MEMORY FOR REAL LIFE</span><span>Built with FastAPI · Qdrant · Lyzr</span></footer>
        </div>
      </main>
    </div>
  );
}

function Landing({ onEnter }) {
  return <main className="landing-shell">
    <div className="landing-noise" />
    <nav className="landing-nav"><a className="landing-brand" href="#top"><span className="brand-mark">r<span>.</span></span><span>RECEIPTS<small>MEMORY, WITH A PAPER TRAIL</small></span></a><div className="landing-nav-links"><a href="#why">THE IDEA</a><a href="#how">HOW IT WORKS</a><button onClick={onEnter}>Open memory desk <span>↗</span></button></div></nav>
    <section className="landing-hero" id="top"><div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line" /> YOUR BRAIN HAS ENOUGH TABS OPEN</div><h1>Some things<br />deserve a <em>receipt.</em></h1><p className="landing-lede">The decision you made. The thing you promised. The detail you’ll swear you remembered. RECEIPTS keeps the context, connects the changes, and brings it back when it matters.</p><div className="hero-actions"><button className="primary-button landing-cta" onClick={onEnter}>Step into your memory desk <span>↗</span></button><a className="text-link" href="#how">See how it works <span>↓</span></a></div><div className="hero-footnote"><span className="signal-dot" /> PERSISTENT MEMORY, NOT ANOTHER CHAT WINDOW</div></div>
      <div className="hero-art" aria-label="Illustration of connected memory receipts"><div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" /><div className="glass-sphere sphere-a" /><div className="glass-sphere sphere-b" /><div className="receipt-card receipt-back"><span className="receipt-topline">MEMORY SLIP / 002</span><div className="receipt-mini-line long" /><div className="receipt-mini-line" /><div className="receipt-mini-line medium" /><div className="receipt-stamp">SAVED</div></div><div className="receipt-card receipt-front"><div className="receipt-header"><span>R. / RECEIPTS</span><span>NO. 0001</span></div><div className="receipt-label">DECISION RECORDED</div><h3>“We’re going<br />with the simpler<br /><em>option.</em>”</h3><div className="receipt-divider" /><div className="receipt-row"><span>MEMORY TYPE</span><strong>DECISION</strong></div><div className="receipt-row"><span>RELATIONSHIP</span><strong>NEW → ACTIVE</strong></div><div className="receipt-bottom"><span>CONTEXT KEPT.</span><span>✳</span></div></div><div className="floating-note note-left"><span className="note-icon">↗</span><div><small>COMMITMENT FOUND</small><strong>“Send it tomorrow”</strong></div><span className="note-dot" /></div><div className="floating-note note-right"><span className="note-icon violet">⌕</span><div><small>SEMANTIC SEARCH</small><strong>Context connected</strong></div></div><div className="art-caption">A SMALL RECEIPT FOR A BIGGER MEMORY <span>✳</span></div></div>
    </section>
    <section className="ticker" aria-label="Product capabilities"><span>CAPTURE WHAT MATTERS</span><b>✳</b><span>REMEMBER THE WHY</span><b>✳</b><span>NOTICE WHAT CHANGED</span><b>✳</b><span>FOLLOW THROUGH</span><b>✳</b></section>
    <section className="manifesto" id="why"><div className="manifesto-side"><span className="section-kicker">A DIFFERENT KIND OF MEMORY</span><span className="manifesto-number">01—04</span></div><div className="manifesto-main"><h2>Chat forgets.<br /><em>A paper trail connects.</em></h2><p>RECEIPTS turns everyday language into structured, searchable memory. When a new decision replaces an old one, the story doesn’t disappear. The record gets smarter.</p><div className="manifesto-tags"><span>DECISIONS</span><span>COMMITMENTS</span><span>CHANGES</span><span>FOLLOW-UPS</span></div></div></section>
    <section className="how-section" id="how"><div className="how-heading"><div><span className="section-kicker">A LITTLE CONTEXT ENGINE</span><h2>Say it once.<br /><em>Find it when it counts.</em></h2></div><p>One simple flow, with a few very deliberate jobs.</p></div><div className="how-grid"><HowCard number="01" title="Speak or write" detail="Capture a thought in natural language. Voice-first input can flow in through Omi when configured." symbol="◌" /><HowCard number="02" title="Make it make sense" detail="Lyzr helps identify decisions, commitments, and useful details hiding in the message." symbol="✳" /><HowCard number="03" title="Keep the thread" detail="Qdrant stores searchable memory so related context can be retrieved and compared later." symbol="⌘" /></div></section>
    <section className="landing-bottom"><div className="bottom-orb" /><div><span className="section-kicker">YOUR CONTEXT IS WORTH KEEPING</span><h2>Let’s keep<br /><em>the receipt.</em></h2></div><button className="primary-button landing-cta" onClick={onEnter}>Open RECEIPTS <span>↗</span></button></section>
    <footer className="landing-footer"><span className="landing-brand small-brand"><span className="brand-mark">r<span>.</span></span><span>RECEIPTS<small>MEMORY, WITH A PAPER TRAIL</small></span></span><span>AN EXPERIMENT IN PERSISTENT MEMORY</span><span>FASTAPI · QDRANT · LYZR</span></footer>
  </main>;
}

function HowCard({ number, title, detail, symbol }) {
  return <article className="how-card glass-panel"><div className="how-card-top"><span>{number} / STEP</span><span className="how-symbol">{symbol}</span></div><h3>{title}</h3><p>{detail}</p><div className="how-card-line" /></article>;
}

function StatCard({ label, value, foot, mark }) {
  return <article className="stat-card glass-panel"><div className="stat-top"><span>{label}</span><span className="stat-mark">{mark}</span></div><div className="stat-value">{value}</div><div className="stat-foot"><span />{foot}</div></article>;
}
function ResultMetric({ label, value }) { return <div className="result-metric"><strong>{value}</strong><span>{label}</span></div>; }
function WorkflowStep({ number, title, detail, last }) {
  return <div className={`workflow-step ${last ? "last" : ""}`}><div className="step-number">{number}</div><div className="step-copy"><strong>{title}</strong><small>{detail}</small></div><span className="step-check">✓</span></div>;
}

function ArchitectureDiagram() {
  const [active, setActive] = useState("fastapi");
  const nodes = [
    { id: "omi", number: "01", title: "Omi", subtitle: "Voice capture", description: "Omi can capture spoken input and send transcripts to the configured FastAPI webhook. This path depends on webhook setup.", kind: "source" },
    { id: "dashboard", number: "02", title: "React dashboard", subtitle: "Manual capture + search", description: "The dashboard sends text to /memories/extract and retrieves matching memories through /memories/search.", kind: "frontend" },
    { id: "fastapi", number: "03", title: "FastAPI", subtitle: "Backend API", description: "Receives dashboard requests and handles extraction, memory creation, retrieval, and related processing.", kind: "backend" },
    { id: "lyzr", number: "04", title: "Lyzr", subtitle: "Extraction service", description: "Processes natural-language input and identifies candidate memories for the backend.", kind: "agent" },
    { id: "logic", number: "05", title: "Memory processing", subtitle: "Deduplication + decisions", description: "Checks for duplicate memories and evaluates decision changes before saving records.", kind: "logic" },
    { id: "qdrant", number: "06", title: "Qdrant", subtitle: "Persistent storage", description: "Stores memory vectors and supports semantic retrieval of related context.", kind: "storage" },
  ];
  const selected = nodes.find((node) => node.id === active) || nodes[2];
  return <section className="panel architecture-panel glass-panel" id="architecture"><div className="panel-heading"><div><div className="section-kicker">03 / UNDER THE HOOD</div><h2>A memory is a team sport<span className="heading-period">.</span></h2><p>Pick a component to see its part in the paper trail.</p></div><span className="architecture-badge"><i /> SYSTEM MAP</span></div><div className="architecture-layout"><div className="architecture-canvas"><div className="architecture-lane-label">INPUT LAYER</div><div className="architecture-node-grid">{nodes.slice(0, 2).map((node) => <ArchitectureNode key={node.id} node={node} active={active === node.id} onClick={() => setActive(node.id)} />)}</div><div className="architecture-down-arrow"><span>↓</span><small>TEXT / TRANSCRIPT</small></div><div className="architecture-lane-label">PROCESSING LAYER</div><div className="architecture-node-grid three-columns">{nodes.slice(2, 5).map((node) => <ArchitectureNode key={node.id} node={node} active={active === node.id} onClick={() => setActive(node.id)} />)}</div><div className="architecture-down-arrow"><span>↓</span><small>EMBED + PERSIST</small></div><div className="architecture-lane-label">MEMORY LAYER</div><div className="architecture-node-grid"><ArchitectureNode node={nodes[5]} active={active === "qdrant"} onClick={() => setActive("qdrant")} /></div><div className="architecture-return-path">↶ Retrieved context returns to the dashboard</div></div><aside className="architecture-details" aria-live="polite"><span className="detail-number">{selected.number}</span><div className="architecture-detail-label">COMPONENT NOTE</div><h3>{selected.title}</h3><p>{selected.description}</p><span className="detail-kind">{selected.subtitle}</span></aside></div><div className="architecture-legend"><span><i className="legend-dot input-dot" /> Input</span><span><i className="legend-dot process-dot" /> Processing</span><span><i className="legend-dot storage-dot" /> Storage</span></div></section>;
}
function ArchitectureNode({ node, active, onClick }) {
  return <button type="button" className={`architecture-node ${node.kind} ${active ? "is-active" : ""}`} onClick={onClick}><span className="architecture-node-top"><span className="architecture-node-icon">{node.number}</span><span className="architecture-node-dot" /></span><strong>{node.title}</strong><small>{node.subtitle}</small></button>;
}

export default App;
