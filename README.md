<div align="center">

# 🛡️ AIP_SAK
### Autonomous AI Penetration Testing & Continuous Surface Security Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE.md)
[![Type Checked](https://img.shields.io/badge/Mypy-Strict-informational.svg?style=for-the-badge&logo=python)](pyproject.toml)
[![Architecture](https://img.shields.io/badge/Architecture-Deterministic%20FSM-purple.svg?style=for-the-badge)](docs/ARCHITECTURE.md)
[![Status](https://img.shields.io/badge/Quality%20Gate-100%25%20Passing%20(66%2F66)-success.svg?style=for-the-badge)](tests/)

<p align="center">
  <b>AIP_SAK</b> (Autonomous AI Penetration Testing — Swiss Army Knife) is an enterprise-grade autonomous penetration testing platform combining deterministic finite state machines, provider-agnostic LLM reasoning, hardened subprocess execution choke points, independent verification oracles, and real-time WebSocket dashboard streaming.
</p>

[Quick Start](#-quick-start) •
[Why AIP_SAK](#-why-aip_sak) •
[Architecture](#-core-architecture) •
[Features](#-key-features) •
[Usage Guide](#-complete-usage-guide) •
[Web Dashboard](#-web-dashboard-ui) •
[Documentation](#-documentation)

---

</div>

## 💡 Why AIP_SAK?

Traditional penetration testing tools operate in silos: network scanners output XML, fuzzers output raw text, web scanners generate hundreds of noisy false positives, and operators manually correlate outputs into reports. 

Generic "AI agent" pentesting frameworks frequently hallucinate nonexistent flags, trigger out-of-scope targets, loop indefinitely without progress, or crash when LLM tokens exhaust budgets.

**AIP_SAK eliminates these problems through 5 fundamental pillars:**

| Pillar | How AIP_SAK Solves It |
|---|---|
| **Deterministic Rails** | An 8-phase finite state machine (`SCOPE` $\rightarrow$ `REPORT`) drives execution. If LLMs fail or `--no-llm` is selected, static policy routers complete the pentest autonomously. |
| **Strict Choke Point** | Exactly **one** module in the entire platform (`src/venice_pt/exec/runner.py`) is allowed to spawn subprocesses, enforcing strict CIDR/domain scope allowlists and rate limits. |
| **Zero Hallucination Context** | Raw tool stdout/stderr **never** enters LLM context. Facts are parsed into a normalized Knowledge Graph and rendered into a dense markdown summary strictly $\le 4\text{KB}$. |
| **Zero False Positives** | Findings are treated as *unconfirmed hypotheses* until re-tested by independent verification oracles (e.g. differential timing or reflection checks). Unconfirmed items receive a 60% confidence penalty ($\times 0.4$) and move to the report appendix. |
| **Frozen Core Contracts** | All intra-system data crosses module boundaries via frozen Pydantic schemas under `CONTRACT_VERSION = "1.0.0"` with automated SHA-256 integrity hash verification. |

---

## 🏛️ Core Architecture

```
                                  +---------------------------------------+
                                  |     React 18 + Vite Web Dashboard     |
                                  +-------------------+-------------------+
                                                      | WebSocket / REST
                                                      v
+---------------------------------------------------------------------------------------------------------+
|                                    FastAPI ASGI Server (server/app.py)                                  |
|   • Bearer Token Authentication   • Engagement REST API   • Control Endpoints   • WS Resume Streaming   |
+-----------------------------------------------------+---------------------------------------------------+
                                                      |
                                                      v
+---------------------------------------------------------------------------------------------------------+
|                                  Planner FSM Rails (brain/fsm.py)                                       |
|  [01 SCOPE] -> [02 RECON] -> [03 ENUM] -> [04 VULN] -> [05 NOVEL] -> [06 VALID] -> [07 CHAIN] -> [08 REP]  |
|                                                     |                                                   |
|             +---------------------------------------+---------------------------------------+           |
|             | Dual-Engine Decision Synthesis                                                |           |
|             v                                                                               v           |
|   [LLM Planner Intelligence]                                                    [Deterministic Router]  |
|   • Structured JSON schema enforcement                                          • Rule-based fallback   |
|   • Budget Governor ($USD caps & model downgrades)                              • Guaranteed completion |
+-----------------------------------------------------+---------------------------------------------------+
                                                      |
                                                      v
+---------------------------------------------------------------------------------------------------------+
|                                   Execution Choke Point (exec/runner.py)                                |
|   • CIDR & Domain Scope Enforcer   • Token-Bucket Rate Limiter   • Tool Flag Validation & Sandbox       |
+-----------------------------------------------------+---------------------------------------------------+
                                                      |
         +--------------------------------------------+--------------------------------------------+
         |                                                                                         |
         v                                                                                         v
+-----------------------------------------+                             +-----------------------------------------+
|             Tool Orchestration          |                             |           Independent Oracles           |
| • Nmap        • Subfinder   • HTTPX     |                             | • SQLi Differential Timing              |
| • Nuclei      • Katana      • Ffuf      |                             | • XSS Context Reflection                |
| • DNSX        • WhatWeb     • Docker    |                             | • Blind OOB DNS/HTTP Callback Nonces    |
+--------------------+--------------------+                             +--------------------+--------------------+
                     |                                                                       |
                     +------------------------------------+----------------------------------+
                                                          v
+---------------------------------------------------------------------------------------------------------+
|                                   Knowledge Graph & Event Store                                         |
|   • Immutable SQLite EventLog   • Fact Deduplication   • Attack Chain Synthesis   • CVSS 3.1 & SARIF    |
+---------------------------------------------------------------------------------------------------------+
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Operating System**: Linux (recommended) or Windows / macOS
- **Python**: `>= 3.12`
- **Node.js**: `>= 18.0.0` (for UI dashboard)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/your-org/aip-sak.git
cd aip-sak

# Install Python package and dev dependencies
python -m pip install -e ".[dev]"

# Verify toolchain and local environment
aip-sak doctor
```

### 3. Initialize an Engagement
```bash
aip-sak init my-pentest --target http://127.0.0.1:3000
```
This scaffolds a sandboxed workspace under `engagements/my-pentest/`:
- `scope.yaml` — Authorized target domain and IP CIDR allowlists.
- `events.db` — Immutable SQLite event log with append-only hash chains.
- `state.json` — Checkpointed FSM progress, parameters, and findings.
- `artifacts/` — Raw tool output files and evidence screenshots.

---

## 💻 Complete Usage Guide

### Running an Autonomous Assessment
```bash
# Full autonomous scan with a $2.00 LLM budget cap
aip-sak run --target http://127.0.0.1:3000 --budget 2 --engagement my-pentest

# 100% Deterministic execution (No LLM required / Zero external API calls)
aip-sak run --target http://127.0.0.1:3000 --no-llm --engagement my-pentest

# Scoped execution for specific phases
aip-sak run --target http://127.0.0.1:3000 --phases recon,enum,vuln_scan
```

### Executing a Single Tool via Choke Point
Direct tool runs are validated against scope and rate-limits:
```bash
aip-sak exec --tool nmap --args "-sV -p 80,443" --target 127.0.0.1
```

### Generating Publication Reports
Compile multi-format deliverables directly from engagement telemetry:
```bash
aip-sak report --engagement my-pentest --format html,sarif,csv --output-dir ./reports
```
- **HTML Report** (`reports/my-pentest_report.html`): Executive summaries, risk distribution cards, confirmed findings with PoC payloads, and demoted finding appendices.
- **SARIF Standard** (`reports/my-pentest_findings.sarif`): OASIS SARIF v2.1.0 compliant for GitHub Advanced Security and DefectDojo ingestion.
- **CSV Data** (`reports/my-pentest_findings.csv`): Tabular export with CVSS scores and confidence ratings.

### 24/7 Attack Surface Monitoring Daemon
Monitor your external surface for drift, open ports, and zero-day CVE banners:
```bash
# Run a single monitoring cycle and exit
aip-sak watch --target 127.0.0.1 --once

# Run continuous background monitoring daemon (hourly sweeps)
aip-sak watch --target 127.0.0.1 --interval 3600
```

---

## 🖥️ Web Dashboard UI

`AIP_SAK` includes a real-time reactive dashboard built with React 18, Vite, TypeScript, and Lucide icons.

### Starting the Server & Dashboard
```bash
# 1. Start the FastAPI backend with WebSocket streaming
aip-sak serve --host 127.0.0.1 --port 8000

# 2. In a separate terminal, launch the UI
cd ui
npm install
npm run dev
```

Open **`http://localhost:5173`** in your browser to experience:
- **Phase Timeline Rail**: Visual progression of the active FSM state with budget tracking.
- **Live Terminal Event Stream**: Real-time virtualized feed streaming directly over WebSocket.
- **Verified Findings Drawer**: Interactive severity tags, CVSS ratings, and technical evidence.
- **Instant Control**: One-click **Pause / Resume** execution toggle communicating directly with the backend controller.

---

## ⚡ The 8-Phase Methodology

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│ 01 SCOPE       │ ──> │ 02 RECON       │ ──> │ 03 ENUM        │ ──> │ 04 VULN_SCAN   │
│ Target bounds  │     │ Subfinder/DNSX │     │ Nmap/Katana    │     │ Nuclei/WhatWeb │
└────────────────┘     └────────────────┘     └────────────────┘     └────────────────┘
                                                                             │
┌────────────────┐     ┌────────────────┐     ┌────────────────┐             │
│ 08 REPORT      │ <── │ 07 CHAIN       │ <── │ 06 VALIDATE    │ <── 05 NOVEL_FUZZ
│ HTML/SARIF/CSV │     │ Exploit Chains │     │ Oracles (TP/FP)│     Differential diff
└────────────────┘     └────────────────┘     └────────────────┘
```

1. **SCOPE**: Parses target CIDR/domains, checks local toolchain dependencies, and verifies authorization.
2. **RECON**: Passive and active asset discovery with `subfinder` and `dnsx`.
3. **ENUM**: Port scanning, HTTP endpoint crawling, and service fingerprinting via `nmap`, `httpx`, and `katana`.
4. **VULN_SCAN**: Automated template-based scanning using `nuclei` and content discovery with `ffuf`.
5. **NOVEL_FUZZ**: Differential baseline response fuzzing and blind OOB callback probes.
6. **VALIDATE**: Independent timing and context reflection verification; demotes unconfirmed findings ($\times 0.4$).
7. **CHAIN**: Multi-step attack chain planning (e.g. Information Disclosure + IDOR $\rightarrow$ Account Takeover).
8. **REPORT**: CVSS 3.1 base scoring, risk matrix synthesis, and report compilation.

---

## 📁 Repository Structure

```
├── docs/                      # Architecture, specifications, and runbooks
│   ├── ARCHITECTURE.md
│   ├── RUNBOOK.md
│   └── SPEC.md
├── engagements/               # Sandboxed runtime engagement state (gitignored)
├── systemd/                   # Linux system service units
├── tests/                     # 66 comprehensive unit tests
│   ├── fixtures/              # Golden tool fixtures (nmap, httpx, nuclei...)
│   └── unit/                  # Tests for store, exec, brain, verify, server...
├── ui/                        # React + Vite + TypeScript dashboard application
└── src/venice_pt/
    ├── bootstrap/             # Host distro detection & Docker fallback resolver
    ├── brain/                 # 8-phase FSM, LLM planner & budget governor
    ├── cli/                   # Typer CLI commands (init, run, serve, report...)
    ├── contracts/             # Frozen Pydantic contracts (CONTRACT_VERSION="1.0.0")
    ├── exec/                  # Subprocess runner choke point, scope & rate-limit
    ├── knowledge/             # Deduplicating graph & ≤4KB markdown renderer
    ├── novel/                 # Differential response oracle & attack chains
    ├── parsers/               # 8 normalized tool parsers
    ├── registry/              # Tool capability manifests
    ├── report/                # HTML, SARIF, CSV report generators & CVSS scoring
    ├── server/                # FastAPI application, auth guards & WebSockets
    └── watch/                 # Continuous drift detector & CVE advisory matcher
```

---

## 🛡️ License & Security

- **License**: Released under the permissive [MIT License](LICENSE.md).
- **Security Policy**: Detailed in [SECURITY.md](SECURITY.md). Please report any vulnerabilities responsibly.
