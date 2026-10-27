import { useState, useEffect } from 'react'
import {
  ShieldAlert,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  Terminal,
  Crosshair
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

export function App() {
  const [currentPhase] = useState('recon')
  const [status, setStatus] = useState('running')
  const [target] = useState('http://127.0.0.1:3000')
  const [logs, setLogs] = useState<string[]>([
    '[+] Initialized engagement workspace: autonomous-test',
    '[*] Target locked: http://127.0.0.1:3000',
    '[*] Phase advance: SCOPE -> RECON',
    '[*] Subfinder: 3 subdomains enumerated',
    '[*] HTTPX: probing live targets: 200 OK (nginx/1.24)',
    '[*] Phase advance: RECON -> ENUM',
    '[*] Nmap: 2 ports open (80/http, 443/https)',
    '[*] Katana: crawler identified 41 endpoints and form actions',
    '[*] Phase advance: ENUM -> VULN_SCAN',
    '[*] Nuclei: exposed .git/config flagged (medium)',
    '[*] Verification oracle: testing timing differential payload',
    '[+] Confirmed True Positive: SQL Injection in /api/users?id=1',
  ])

  const [findings] = useState<Finding[]>([
    {
      id: 'F-001',
      title: 'SQL Injection via id parameter',
      severity: 'critical',
      target: 'http://127.0.0.1:3000/api/users',
      confidence: 0.95,
      verified: true,
    },
    {
      id: 'F-002',
      title: 'Exposed .git/config',
      severity: 'medium',
      target: 'http://127.0.0.1:3000/.git/config',
      confidence: 0.85,
      verified: true,
    },
    {
      id: 'F-003',
      title: 'Swagger API Documentation Disclosed',
      severity: 'info',
      target: 'http://127.0.0.1:3000/api-docs',
      confidence: 0.90,
      verified: true,
    },
  ])

  // Poll engagement state or establish WS connection
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
            setStatus(data.action === 'pause' ? 'paused' : 'running')
          }
          setLogs((prev) => [...prev, `[*] WS Event: ${JSON.stringify(data)}`])
        } catch {
          setLogs((prev) => [...prev, `[*] ${event.data}`])
        }
      }
    } catch {
      // Standalone dev server fallback
    }

    return () => {
      if (ws) ws.close()
    }
  }, [])

  const toggleControl = async () => {
    const action = status === 'running' ? 'pause' : 'resume'
    try {
      await fetch('/api/control', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer venice-secret-token',
        },
        body: JSON.stringify({
          action,
          engagement: 'autonomous-test',
        }),
      })
      setStatus(action === 'pause' ? 'paused' : 'running')
    } catch {
      setStatus(action === 'pause' ? 'paused' : 'running')
    }
  }

  return (
    <div className="dashboard-layout">
      {/* Top Navbar */}
      <header className="top-nav">
        <div className="brand">
          <ShieldAlert size={24} color="#6366f1" />
          <span>venice-pt</span>
          <span className="brand-badge">AUTONOMOUS</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem' }}>
            <Crosshair size={16} color="#94a3b8" />
            <span style={{ color: '#94a3b8' }}>Target:</span>
            <code>{target}</code>
          </div>

          <div className="status-pill">
            <span className="status-dot" style={{ backgroundColor: status === 'running' ? '#10b981' : '#f59e0b' }} />
            <span>{status.toUpperCase()}</span>
          </div>

          <button className="btn btn-secondary" onClick={toggleControl}>
            {status === 'running' ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Pause size={14} /> Pause
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Play size={14} /> Resume
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Main 3-column Layout */}
      <main className="main-content">
        {/* Left: Phase Rail & Metrics */}
        <section className="panel">
          <div className="panel-header">
            <span>FSM Execution Rail</span>
            <Activity size={16} />
          </div>
          <div className="phase-rail">
            {PHASES.map((p, idx) => {
              const isActive = p === currentPhase
              return (
                <div key={p} className={`phase-node ${isActive ? 'active' : ''}`}>
                  <span style={{ opacity: 0.6, fontSize: '0.75rem', width: 20 }}>0{idx + 1}</span>
                  <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>{p}</span>
                  {isActive && <span style={{ marginLeft: 'auto', fontSize: '0.75rem' }}>ACTIVE</span>}
                </div>
              )
            })}
          </div>

          <div style={{ marginTop: 'auto', paddingTop: 20, borderTop: '1px solid var(--border)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>Budget Spent</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>$0.12 <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>/ $2.00</span></div>
          </div>
        </section>

        {/* Center: Live Terminal Event Stream */}
        <section className="panel">
          <div className="panel-header">
            <span>Live Event Stream</span>
            <Terminal size={16} />
          </div>
          <div className="log-stream">
            {logs.map((log, i) => (
              <div key={i} className="log-entry">
                {log}
              </div>
            ))}
          </div>
        </section>

        {/* Right: Findings Drawer */}
        <section className="panel">
          <div className="panel-header">
            <span>Verified Findings ({findings.length})</span>
            <AlertTriangle size={16} />
          </div>
          <div className="findings-list">
            {findings.map((f) => (
              <div key={f.id} className="finding-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span className={`sev-badge sev-${f.severity}`}>{f.severity}</span>
                  <span style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={12} /> VERIFIED
                  </span>
                </div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 6 }}>{f.title}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <code>{f.target}</code>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
                  Confidence: <strong>{(f.confidence * 100).toFixed(0)}%</strong>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  )
}
export default App
