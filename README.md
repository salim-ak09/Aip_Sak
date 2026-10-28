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

## 💻 Complete Usage Guide & Command Reference

### CLI Commands Overview

| Command | Description | Example |
|---|---|---|
| [`aip-sak init`](#1-initialize-an-engagement-aip-sak-init) | Scaffolds a sandboxed workspace and scope definition | `aip-sak init my-lab --target https://example.com` |
| [`aip-sak doctor`](#2-system-diagnostics--toolchain-aip-sak-doctor) | Checks prerequisites, OS capability, and security toolchain | `aip-sak doctor --install` |
| [`aip-sak ai`](#3-ai-agent-diagnostics--latency-test-aip-sak-ai) | Tests AI provider connectivity, model latency, and token response | `aip-sak ai` |
| [`aip-sak run`](#4-run-autonomous-assessment-aip-sak-run) | Executes the 8-phase autonomous pentest assessment | `aip-sak run --target https://example.com --budget 2` |
| [`aip-sak status`](#5-live-status--progress-aip-sak-status) | Shows current phase, findings count, spend, and tool states | `aip-sak status --engagement my-lab` |
| [`aip-sak scope`](#6-inspect-target-scope-aip-sak-scope) | Displays authorized domains, CIDRs, and excluded targets | `aip-sak scope --engagement my-lab` |
| [`aip-sak tools`](#7-list-registered-security-tools-aip-sak-tools) | Lists all supported scanners, parsers, and binary locations | `aip-sak tools` |
| [`aip-sak exec`](#8-execute-a-single-tool-via-choke-point-aip-sak-exec) | Executes an isolated tool under strict scope enforcement | `aip-sak exec --tool nmap --args "-sV -p 80,443" --target 127.0.0.1` |
| [`aip-sak report`](#9-generate-reports-aip-sak-report) | Compiles executive & technical reports (HTML, SARIF, CSV) | `aip-sak report --engagement my-lab --format html,sarif,csv` |
| [`aip-sak serve`](#10-start-api--dashboard-backend-aip-sak-serve) | Launches the FastAPI REST & WebSocket streaming server | `aip-sak serve --host 127.0.0.1 --port 8000` |
| [`aip-sak watch`](#11-continuous-247-attack-surface-monitor-aip-sak-watch) | Continuous monitoring daemon for new ports and CVE advisories | `aip-sak watch --target example.com --interval 3600` |
| [`aip-sak replay`](#12-event-log-replay--forensics-aip-sak-replay) | Replays SQLite event logs and reconstructs graph projections | `aip-sak replay --engagement my-lab` |

---

### Detailed Command Documentation

#### 1. Initialize an Engagement (`aip-sak init`)
Creates an isolated directory under `engagements/<name>/` with YAML target scoping rules, SQLite append-only log, and checkpoint files.
```bash
# Basic initialization
aip-sak init my-lab --target https://example.com/

# Custom engagement naming
aip-sak init corporate-audit --target 192.168.1.0/24
```

#### 2. System Diagnostics & Toolchain (`aip-sak doctor`)
Verifies execution environment, Python dependencies, Docker fallbacks, and security binaries (`nmap`, `subfinder`, `nuclei`, `httpx`, `katana`, `ffuf`, `dnsx`).
```bash
# Human-readable diagnostics table
aip-sak doctor

# Machine-readable JSON output
aip-sak doctor --json

# Attempt automatic installation of missing binaries
aip-sak doctor --install
```

#### 3. AI Agent Diagnostics & Latency Test (`aip-sak ai`)
Inspects active AI settings from `.env`, tests live authentication with Google Gemini or OpenAI, and reports response latency, token count, and cost.
```bash
# Run default connectivity check
aip-sak ai

# Test custom reasoning prompt
aip-sak ai --prompt "Analyze risk for SQL injection in password reset parameter."
```

#### 4. Run Autonomous Assessment (`aip-sak run`)
Drives the 8-phase finite state machine (`SCOPE` $\rightarrow$ `RECON` $\rightarrow$ `ENUM` $\rightarrow$ `VULN_SCAN` $\rightarrow$ `NOVEL_FUZZ` $\rightarrow$ `VALIDATE` $\rightarrow$ `CHAIN` $\rightarrow$ `REPORT`).
```bash
# Standard autonomous run with budget governor ($2.00 max spend)
aip-sak run --target https://example.com/ --budget 2

# Explicitly link to an initialized workspace
aip-sak run --engagement my-lab --target https://example.com/ --budget 2

# Select specific AI provider (gemini, openai, ollama)
aip-sak run --target https://example.com/ --provider gemini --budget 1.5

# 100% Deterministic mode (Zero external AI calls, pure security heuristics)
aip-sak run --target https://example.com/ --no-llm

# Resume an interrupted or paused scan from last checkpoint
aip-sak run --resume --target https://example.com/

# Run only designated phases
aip-sak run --target https://example.com/ --phases recon,enum,vuln_scan

# Set risk ceiling (passive, safe, intrusive, destructive)
aip-sak run --target https://example.com/ --risk safe
```

#### 5. Live Status & Progress (`aip-sak status`)
Inspects engagement health, observed facts count, confirmed vulnerabilities, and budget consumed.
```bash
aip-sak status --engagement my-lab
```

#### 6. Inspect Target Scope (`aip-sak scope`)
Validates authorized scope boundaries, including CIDR blocks, allowed domain regex patterns, and excluded assets.
```bash
aip-sak scope --engagement my-lab
```

#### 7. List Registered Security Tools (`aip-sak tools`)
Displays all integrated security scanners, their risk category, capability flags, and installation path.
```bash
aip-sak tools
```

#### 8. Execute a Single Tool via Choke Point (`aip-sak exec`)
Runs an individual tool through the secure execution runner, validating input flags and target scope before firing subprocesses.
```bash
# Run Nmap service detection
aip-sak exec --tool nmap --args "-sV -p 80,443" --target 127.0.0.1 --engagement my-lab

# Run Subfinder subdomain discovery
aip-sak exec --tool subfinder --args "-silent" --target example.com --engagement my-lab
```

#### 9. Generate Reports (`aip-sak report`)
Transforms raw event telemetry and the knowledge graph into publication-grade deliverables.
```bash
# Generate all report formats into ./reports/
aip-sak report --engagement my-lab --format html,sarif,csv --output-dir ./reports

# Generate only executive HTML report
aip-sak report --engagement my-lab --format html
```

#### 10. Start API & Dashboard Backend (`aip-sak serve`)
Starts the FastAPI application with live WebSocket event streaming, operator chat endpoints, and REST API controllers.
```bash
# Default on localhost:8000
aip-sak serve

# Custom host and port
aip-sak serve --host 0.0.0.0 --port 8080
```

#### 11. Continuous 24/7 Attack Surface Monitor (`aip-sak watch`)
Monitors target hosts over time, alerting on newly discovered ports, web technology changes, and emerging CVE vulnerabilities.
```bash
# Single sweep and exit
aip-sak watch --target example.com --once

# Continuous hourly sweep
aip-sak watch --target example.com --interval 3600
```

#### 12. Event Log Replay & Forensics (`aip-sak replay`)
Replays past engagement event logs to audit decision paths, verify data integrity, or test new parser logic without re-scanning.
```bash
# Replay live engagement events
aip-sak replay --engagement my-lab

# Replay demo synthetic event log
aip-sak replay --demo
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
