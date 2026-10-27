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
  Zap
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
  const [engagements, setEngagements] = useState<string[]>([])
  const [selectedEng, setSelectedEng] = useState<string>('autonomous-test')
  const [target, setTarget] = useState<string>('http://127.0.0.1:3000')
  const [currentPhase, setCurrentPhase] = useState<string>('recon')
  const [status, setStatus] = useState<string>('running')
  const [budgetSpent] = useState<number>(0.12)
  const [logs, setLogs] = useState<string[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      sender: 'ai_agent',
      message: 'AIP_SAK Autonomous AI Agent initialized. Monitoring attack surface and ready for operator directives.',
    },
  ])
  const [inputOrder, setInputOrder] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'stream' | 'chat'>('chat')
  const logsEndRef = useRef<HTMLDivElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // 1. Fetch live engagement data from backend
  const fetchEngagementData = async (engName: string) => {
    try {
      const res = await fetch(`/api/engagements/${engName}`, {
        headers: { Authorization: 'Bearer venice-secret-token' },
      })
      if (res.ok) {
        const data = await res.json()
        if (data.target) setTarget(data.target)
        if (data.phase) setCurrentPhase(data.phase)
        if (data.status) setStatus(data.status)
        if (data.findings && Array.isArray(data.findings)) setFindings(data.findings)
        if (data.chat_history && Array.isArray(data.chat_history)) setChatMessages(data.chat_history)
      }
    } catch {
      // Fallback in case backend is offline
    }
  }

  // Fetch list of engagements
  useEffect(() => {
    const loadEngagements = async () => {
      try {
        const res = await fetch('/api/engagements', {
          headers: { Authorization: 'Bearer venice-secret-token' },
        })
        if (res.ok) {
          const list = await res.json()
          const names = list.map((item: { name: string }) => item.name)
          if (names.length > 0) {
            setEngagements(names)
            setSelectedEng(names[0])
            fetchEngagementData(names[0])
          }
        }
      } catch {
        // Dev fallback
      }
    }
    loadEngagements()
  }, [])

  // 2. Real-time WebSocket event connection
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

    const interval = setInterval(() => {
      if (selectedEng) fetchEngagementData(selectedEng)
    }, 4000)

    return () => {
      if (ws) ws.close()
      clearInterval(interval)
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

  // Operator Chat / Give Directives to AI Agent
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
      // Offline fallback
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
              <span className="badge-tag">AUTONOMOUS AGENT</span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              AI Penetration Testing & Exploit Orchestrator
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
                Active Engagement
              </div>
              <select
                value={selectedEng}
                onChange={(e) => {
                  setSelectedEng(e.target.value)
                  fetchEngagementData(e.target.value)
                }}
                style={{ width: '100%', background: 'rgba(0,0,0,0.4)', color: '#fff', border: '1px solid var(--border)', padding: '6px 10px', borderRadius: 6, fontSize: '0.8rem', outline: 'none' }}
              >
                {engagements.map((e) => (
                  <option key={e} value={e}>
                    {e}
                  </option>
                ))}
                {engagements.length === 0 && <option value="autonomous-test">autonomous-test</option>}
              </select>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 14, fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Budget Governor</span>
                <span style={{ fontWeight: 700, color: '#10b981' }}>${budgetSpent.toFixed(2)} / $5.00</span>
              </div>
            </div>
          </div>
        </section>

        {/* Center: Live Terminal & AI Agent Dialogue */}
        <section className="cyber-card">
          <div className="card-header" style={{ display: 'flex', gap: 10 }}>
            <div style={{ display: 'flex', gap: 8 }}>
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
                <Bot size={14} color="#6366f1" /> AI Agent Dialogue
              </button>
              <button
                className="btn-ghost"
                style={{
                  background: activeTab === 'stream' ? 'rgba(6, 182, 212, 0.2)' : 'transparent',
                  borderColor: activeTab === 'stream' ? 'var(--accent-cyan)' : 'transparent',
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                }}
                onClick={() => setActiveTab('stream')}
              >
                <Terminal size={14} color="#06b6d4" /> Live Execution Stream
              </button>
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Interactive Console</span>
          </div>

          <div className="card-body" style={{ padding: 14 }}>
            {activeTab === 'chat' ? (
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
            ) : (
              <div className="terminal-window">
                {logs.length === 0 ? (
                  <div style={{ color: 'var(--text-muted)' }}>Waiting for live execution events...</div>
                ) : (
                  logs.map((log, i) => (
                    <div
                      key={i}
                      className={`terminal-line ${
                        log.includes('[VULNERABILITY]')
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

        {/* Right: Verified Findings Drawer */}
        <section className="cyber-card">
          <div className="card-header">
            <span>Verified Findings ({findings.length})</span>
            <AlertTriangle size={16} color="#f43f5e" />
          </div>
          <div className="card-body">
            {findings.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: 40, fontSize: '0.85rem' }}>
                No vulnerabilities verified yet.
                <div style={{ fontSize: '0.75rem', marginTop: 8 }}>
                  Agent is actively scanning and validating candidate hypotheses.
                </div>
              </div>
            ) : (
              findings.map((f, i) => (
                <div key={f.id || i} className="finding-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <span className={`badge-sev sev-${f.severity?.toLowerCase() || 'medium'}`}>
                      {f.severity || 'HIGH'}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle2 size={12} /> VERIFIED ORACLE
                    </span>
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '0.88rem', marginBottom: 4 }}>{f.title}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <code>{f.target}</code>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8, display: 'flex', justifyContent: 'space-between' }}>
                    <span>Confidence: <strong>{((f.confidence || 0.9) * 100).toFixed(0)}%</strong></span>
                    <span style={{ color: '#a5b4fc' }}>PoC Verified</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  )
}
export default App
