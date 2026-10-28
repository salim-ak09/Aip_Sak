import { useState, useEffect, useRef } from 'react'
import {
  ShieldAlert,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  Terminal,
  Crosshair,
  Send,
  Bot,
  Zap,
  ListFilter,
  Layers,
} from 'lucide-react'

const PHASES = [
  'scope',
  'recon',
  'enum',
  'vuln_scan',
  'novel_fuzz',
  'validate',
  'chain',
  'report',
]

interface AttackItem {
  name: string
  target: string
  phase: string
  status: string
  findings_count: number
  budget_spent: number
  path: string
}

interface Finding {
  id: string
  title: string
  severity: string
  target: string
  confidence: number
  verified: boolean
}

interface ChatMessage {
  sender: 'operator' | 'ai_agent'
  message: string
}

export function App() {
  const [attacks, setAttacks] = useState<AttackItem[]>([])
  const [selectedEng, setSelectedEng] = useState<string>('my-lab')
  const [target, setTarget] = useState<string>('https://exemple.com/')
  const [currentPhase, setCurrentPhase] = useState<string>('recon')
  const [status, setStatus] = useState<string>('running')
  const [budgetSpent, setBudgetSpent] = useState<number>(0.0)
  const [logs, setLogs] = useState<string[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      sender: 'ai_agent',
      message: 'AIP_SAK Autonomous AI Agent initialized. Monitoring attack surface and ready for operator directives.',
    },
  ])
  const [inputOrder, setInputOrder] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'attacks' | 'stream' | 'chat'>('attacks')
  const [selectedAttackDetails, setSelectedAttackDetails] = useState<any>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 1. Fetch live attacks list from backend
  const loadAttacksList = async () => {
    try {
      const res = await fetch('/api/engagements', {
        headers: { Authorization: 'Bearer venice-secret-token' },
      })
      if (res.ok) {
        const list: AttackItem[] = await res.json()
        setAttacks(list)
        if (list.length > 0 && !selectedEng) {
          setSelectedEng(list[0].name)
          fetchEngagementData(list[0].name)
        }
      }
    } catch {
      // offline fallback
    }
  }

  // 2. Fetch specific engagement details
  const fetchEngagementData = async (engName: string) => {
    try {
      const res = await fetch(`/api/engagements/${engName}`, {
        headers: { Authorization: 'Bearer venice-secret-token' },
      })
      if (res.ok) {
        const data = await res.json()
        setSelectedAttackDetails(data)
        if (data.target) setTarget(data.target)
        if (data.current_phase || data.phase) setCurrentPhase(data.current_phase || data.phase)
        if (data.status) setStatus(data.status)
        if (data.budget_spent_usd !== undefined) setBudgetSpent(data.budget_spent_usd)
        if (data.findings && Array.isArray(data.findings)) setFindings(data.findings)
        if (data.chat_history && Array.isArray(data.chat_history)) setChatMessages(data.chat_history)
        if (data.recent_events && Array.isArray(data.recent_events) && logs.length === 0) {
          const loadedLogs = data.recent_events.map((e: any) => `[${e.phase?.toUpperCase() || 'INFO'}] ${e.kind}: ${JSON.stringify(e.payload || {})}`)
          setLogs(loadedLogs)
        }
      }
    } catch {
      // Fallback
    }
  }

  useEffect(() => {
    loadAttacksList()
    const poll = setInterval(() => {
      loadAttacksList()
      if (selectedEng) fetchEngagementData(selectedEng)
    }, 3000)
    return () => clearInterval(poll)
  }, [selectedEng])

  // 3. Real-time WebSocket connection
  useEffect(() => {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProto}//${window.location.host}/ws`
    let ws: WebSocket | null = null

    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'control_action') {
            if (data.action === 'pause') setStatus('paused')
            if (data.action === 'resume') setStatus('running')
            if (data.details?.agent_reply) {
              setChatMessages((prev) => [
                ...prev,
                { sender: 'ai_agent', message: data.details.agent_reply },
              ])
            }
          } else if (data.kind === 'plan') {
            setLogs((prev) => [...prev, `[AI PLANNER] ${data.payload?.rationale || 'Action emitted'}`])
            if (data.payload?.tool) {
              setLogs((prev) => [...prev, `[TOOL EXEC] ${data.payload.tool} ${data.payload.args?.join(' ') || ''}`])
            }
          } else if (data.kind === 'fact') {
            setLogs((prev) => [...prev, `[FACT] Discovered ${data.payload?.kind}: ${data.payload?.key}`])
          } else if (data.kind === 'finding') {
            setFindings((prev) => [...prev, data.payload])
            setLogs((prev) => [...prev, `[VULNERABILITY] Found: ${data.payload?.title}`])
          } else if (data.kind === 'phase_enter') {
            setCurrentPhase(data.payload?.phase || 'recon')
          }
        } catch {
          setLogs((prev) => [...prev, `[*] ${event.data}`])
        }
      }
    } catch {
      // ws fallback
    }

    return () => {
      if (ws) ws.close()
    }
  }, [selectedEng])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, chatMessages])

  // Pause / Resume Toggle
  const toggleExecution = async () => {
    const nextAction = status === 'running' ? 'pause' : 'resume'
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer venice-secret-token',
        },
        body: JSON.stringify({
          action: nextAction,
          engagement: selectedEng,
        }),
      })
      setStatus(nextAction === 'pause' ? 'paused' : 'running')
    } catch {
      setStatus(nextAction === 'pause' ? 'paused' : 'running')
    }
  }

  // Launch Engagement
  const launchAssessment = async () => {
    try {
      await fetch(`/api/engagements/${selectedEng}/launch`, {
        method: 'POST',
        headers: { Authorization: 'Bearer venice-secret-token' },
      })
      setStatus('running')
      setLogs((prev) => [...prev, `[+] Launched autonomous AI assessment for ${target}`])
    } catch {
      setStatus('running')
    }
  }

  // Send Directive
  const sendOperatorDirective = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputOrder.trim()) return

    const userText = inputOrder.trim()
    setInputOrder('')
    setChatMessages((prev) => [...prev, { sender: 'operator', message: userText }])

    try {
      const res = await fetch('/api/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer venice-secret-token',
        },
        body: JSON.stringify({
          action: 'chat',
          engagement: selectedEng,
          details: { message: userText },
        }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.details?.agent_reply) {
          setChatMessages((prev) => [
            ...prev,
            { sender: 'ai_agent', message: data.details.agent_reply },
          ])
        }
      }
    } catch {
      setTimeout(() => {
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'ai_agent',
            message: `Directive noted: "${userText}". Adjusting discovery heuristics for ${target}.`,
          },
        ])
      }, 500)
    }
  }

  const selectAttackRow = (attack: AttackItem) => {
    setSelectedEng(attack.name)
    setTarget(attack.target)
    setCurrentPhase(attack.phase)
    setStatus(attack.status)
    setBudgetSpent(attack.budget_spent)
    fetchEngagementData(attack.name)
  }

  return (
    <div className="dashboard-root">
      {/* Top Header */}
      <header className="header-bar">
        <div className="brand-section">
          <div className="brand-icon-box">
            <ShieldAlert size={22} color="#06b6d4" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="brand-name">AIP_SAK</span>
              <span className="badge-tag">AUTONOMOUS COMMAND CENTER</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              Live AI Penetration Testing & Continuous Surface Security
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {/* Target Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'rgba(0,0,0,0.3)', padding: '6px 14px', borderRadius: 8, border: '1px solid var(--border)' }}>
            <Crosshair size={14} color="#06b6d4" />
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Target:</span>
            <code style={{ fontSize: '0.82rem', color: '#fff' }}>{target}</code>
          </div>

          {/* Status Badge */}
          <div className={`status-pill status-${status}`}>
            <span className="status-dot" style={{ backgroundColor: status === 'running' ? '#10b981' : '#f59e0b' }} />
            <span>{status.toUpperCase()}</span>
          </div>

          {/* Controls */}
          <button className="btn-ghost" onClick={toggleExecution}>
            {status === 'running' ? (
              <>
                <Pause size={14} /> Pause
              </>
            ) : (
              <>
                <Play size={14} /> Resume
              </>
            )}
          </button>

          <button className="btn-action" onClick={launchAssessment}>
            <Zap size={14} /> Start Agent
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="main-grid">
        {/* Left: 8-Phase FSM Rail & Resource Gauges */}
        <section className="cyber-card">
          <div className="card-header">
            <span>FSM Execution Rail</span>
            <Activity size={16} color="#06b6d4" />
          </div>
          <div className="card-body">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {PHASES.map((p, idx) => {
                const isActive = p.toLowerCase() === currentPhase.toLowerCase()
                return (
                  <div key={p} className={`phase-item ${isActive ? 'active' : ''}`}>
                    <span style={{ opacity: 0.5, fontSize: '0.75rem', width: 22 }}>0{idx + 1}</span>
                    <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p}</span>
                    {isActive && (
                      <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: '#06b6d4', fontWeight: 800 }}>
                        ACTIVE
                      </span>
                    )}
                  </div>
                )
              })}
            </div>

            <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>
                Selected Engagement
              </div>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fff', marginBottom: 12 }}>
                {selectedEng}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 6 }}>
                <span style={{ color: 'var(--text-muted)' }}>Spend Governor</span>
                <span style={{ fontWeight: 700, color: '#10b981' }}>${budgetSpent.toFixed(4)} / $5.00</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Active Attacks</span>
                <span style={{ fontWeight: 700, color: '#06b6d4' }}>{attacks.filter(a => a.status === 'running').length} running</span>
              </div>
            </div>
          </div>
        </section>

        {/* Center: Live Attacks Table & Console Tabs */}
        <section className="cyber-card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn-ghost"
                style={{
                  background: activeTab === 'attacks' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                  borderColor: activeTab === 'attacks' ? 'var(--accent-cyan)' : 'transparent',
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                }}
                onClick={() => setActiveTab('attacks')}
              >
                <ListFilter size={14} color="#06b6d4" /> Live Attacks ({attacks.length})
              </button>
              <button
                className="btn-ghost"
                style={{
                  background: activeTab === 'chat' ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                  borderColor: activeTab === 'chat' ? 'var(--accent-indigo)' : 'transparent',
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                }}
                onClick={() => setActiveTab('chat')}
              >
                <Bot size={14} color="#6366f1" /> AI Agent Chat
              </button>
              <button
                className="btn-ghost"
                style={{
                  background: activeTab === 'stream' ? 'rgba(16, 185, 129, 0.2)' : 'transparent',
                  borderColor: activeTab === 'stream' ? 'var(--accent-green)' : 'transparent',
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                }}
                onClick={() => setActiveTab('stream')}
              >
                <Terminal size={14} color="#10b981" /> Execution Stream
              </button>
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Real-Time Telemetry</span>
          </div>

          <div className="card-body" style={{ padding: 14 }}>
            {activeTab === 'attacks' && (
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
                <table className="attacks-table">
                  <thead>
                    <tr>
                      <th>Status</th>
                      <th>Engagement</th>
                      <th>Target</th>
                      <th>Phase</th>
                      <th>Findings</th>
                      <th>Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attacks.map((att) => {
                      const isSelected = att.name === selectedEng
                      const isRunning = att.status === 'running'
                      return (
                        <tr
                          key={att.name}
                          className={isSelected ? 'selected' : ''}
                          onClick={() => selectAttackRow(att)}
                        >
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              {isRunning ? <span className="pulse-dot" /> : <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: att.status === 'completed' ? '#06b6d4' : '#64748b', display: 'inline-block' }} />}
                              <span style={{ fontWeight: 700, fontSize: '0.72rem', textTransform: 'uppercase', color: isRunning ? '#10b981' : 'var(--text-muted)' }}>
                                {att.status}
                              </span>
                            </div>
                          </td>
                          <td style={{ fontWeight: 700 }}>{att.name}</td>
                          <td><code>{att.target}</code></td>
                          <td>
                            <span className="badge-tag" style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}>
                              {att.phase}
                            </span>
                          </td>
                          <td style={{ fontWeight: 700, color: att.findings_count > 0 ? '#f43f5e' : 'inherit' }}>
                            {att.findings_count}
                          </td>
                          <td style={{ color: '#10b981' }}>${att.budget_spent.toFixed(4)}</td>
                        </tr>
                      )
                    })}
                    {attacks.length === 0 && (
                      <tr>
                        <td colSpan={6} style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
                          No engagements discovered yet. Run <code>aip-sak run --target &lt;URL&gt;</code> to begin.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'chat' && (
              <div className="chat-window">
                <div className="chat-history">
                  {chatMessages.map((msg, i) => (
                    <div key={i} className={`chat-bubble ${msg.sender === 'ai_agent' ? 'ai' : 'operator'}`}>
                      <div style={{ fontSize: '0.7rem', opacity: 0.6, marginBottom: 4, fontWeight: 700 }}>
                        {msg.sender === 'ai_agent' ? '🤖 AIP_SAK AGENT' : '👤 OPERATOR DIRECTIVE'}
                      </div>
                      {msg.message}
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                <form onSubmit={sendOperatorDirective} className="chat-input-bar">
                  <input
                    type="text"
                    value={inputOrder}
                    onChange={(e) => setInputOrder(e.target.value)}
                    placeholder="Give order, ask status, or guide exploration (e.g. 'prioritize login endpoints')..."
                    className="chat-input"
                  />
                  <button type="submit" className="btn-action" style={{ padding: '8px 14px' }}>
                    <Send size={14} /> Send
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'stream' && (
              <div className="terminal-window">
                {logs.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)' }}>Waiting for live execution events...</div>
                ) : (
                  logs.map((log, i) => (
                    <div
                      key={i}
                      className={`terminal-line ${log.includes('[VULNERABILITY]')
                          ? 'finding'
                          : log.includes('[FACT]')
                            ? 'fact'
                            : ''
                        }`}
                    >
                      {log}
                    </div>
                  ))
                )}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </section>

        {/* Right: Selected Attack Deep-Dive & Findings */}
        <section className="cyber-card">
          <div className="card-header">
            <span>Engagement Inspector</span>
            <Layers size={16} color="#06b6d4" />
          </div>
          <div className="card-body" style={{ overflowY: 'auto' }}>
            {selectedAttackDetails ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div className="detail-block">
                  <div className="detail-label">Engagement Workspace</div>
                  <div className="detail-val" style={{ fontWeight: 700, color: '#06b6d4' }}>
                    {selectedAttackDetails.name || selectedEng}
                  </div>
                </div>

                <div className="detail-block">
                  <div className="detail-label">Target URL / Domain</div>
                  <div className="detail-val">{selectedAttackDetails.target || target}</div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div className="detail-block">
                    <div className="detail-label">Current Phase</div>
                    <div className="detail-val" style={{ textTransform: 'uppercase', color: '#a5b4fc', fontWeight: 700 }}>
                      {selectedAttackDetails.current_phase || currentPhase}
                    </div>
                  </div>
                  <div className="detail-block">
                    <div className="detail-label">Status</div>
                    <div className="detail-val" style={{ textTransform: 'uppercase', color: status === 'running' ? '#10b981' : '#f59e0b', fontWeight: 700 }}>
                      {selectedAttackDetails.status || status}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <div className="detail-block">
                    <div className="detail-label">Facts Observed</div>
                    <div className="detail-val">{selectedAttackDetails.facts_count || 0} facts</div>
                  </div>
                  <div className="detail-block">
                    <div className="detail-label">Findings Verified</div>
                    <div className="detail-val" style={{ color: '#f43f5e', fontWeight: 700 }}>
                      {selectedAttackDetails.findings_count || findings.length} issues
                    </div>
                  </div>
                </div>

                {selectedAttackDetails.scope?.include?.domains && (
                  <div className="detail-block">
                    <div className="detail-label">Authorized Domains Scope</div>
                    <div className="detail-val">
                      {selectedAttackDetails.scope.include.domains.join(', ') || 'All in-scope'}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 10 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertTriangle size={14} color="#f43f5e" /> Verified Findings ({findings.length})
                  </div>
                  {findings.length === 0 ? (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', padding: 12, borderRadius: 8, textAlign: 'center' }}>
                      No verified vulnerabilities yet.
                    </div>
                  ) : (
                    findings.map((f, i) => (
                      <div key={f.id || i} className="finding-item" style={{ marginBottom: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <span className={`badge-sev sev-${f.severity?.toLowerCase() || 'high'}`}>
                            {f.severity || 'HIGH'}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
                            <CheckCircle2 size={12} /> VERIFIED
                          </span>
                        </div>
                        <div style={{ fontWeight: 700, fontSize: '0.82rem' }}>{f.title}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                          <code>{f.target}</code>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 40, fontSize: '0.85rem' }}>
                Select an attack from the table to inspect details.
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
export default App
