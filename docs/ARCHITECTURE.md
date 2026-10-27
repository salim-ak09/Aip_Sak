# aip_Sak System Architecture

## Overview
`aip_Sak` is an autonomous, deterministic-first AI penetration testing platform built in Python 3.12. It combines strict frozen contract schemas, an immutable SQLite event log, an isolated subprocess execution runner, modular parsers and knowledge graph, an 8-phase finite state machine with LLM decision synthesis, independent verification oracles, and real-time WebSocket dashboard streaming.

```
       +-------------------------------------------------------------+
       |                  Web Dashboard (React + Vite)               |
       +------------------------------+------------------------------+
                                      | WebSocket / REST
                                      v
       +-------------------------------------------------------------+
       |                  Server Layer (FastAPI / Uvicorn)           |
       +------------------------------+------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
+-------------------+                                     +-------------------+
|  Watch Service    |                                     |  CLI Workflows    |
|  (Drift & CVE)    |                                     |  (init, run, etc) |
+-------------------+                                     +-------------------+
         |                                                         |
         +----------------------------+----------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |                   Planner FSM (8 Phases)                    |
       |  SCOPE -> RECON -> ENUM -> VULN -> NOVEL -> VALID -> CHAIN  |
       |               [LLM Planner / Static Policy Router]          |
       +------------------------------+------------------------------+
                                      |
         +----------------------------+----------------------------+
         |                                                         |
         v                                                         v
+-------------------+                                     +-------------------+
|  Knowledge Graph  |                                     | Execution Runner  |
|  (Dedup Facts)    |                                     | (Choke Point)     |
+-------------------+                                     +-------------------+
         ^                                                         |
         | Parsers (Nmap, HTTPX, Nuclei, Ffuf, Katana...)          v
         +------------------------------------------------ Tools / Targets
```

## Key Architectural Principles
1. **Frozen Contracts**: All intra-system data crosses module boundaries using Pydantic schemas frozen under `CONTRACT_VERSION = "1.0.0"`.
2. **Deterministic Rails**: If LLM providers fail or `--no-llm` is passed, the deterministic policy router autonomously executes pentests to completion.
3. **Execution Choke Point**: `exec/runner.py` is the only point in the codebase allowed to call subprocesses, enforcing strict scope allowlists and rate limits.
4. **Independent Verification**: Candidate vulnerabilities must be confirmed via separate oracles before being marked verified. Unconfirmed findings have confidence penalized ($\times 0.4$) to eliminate false positives.
