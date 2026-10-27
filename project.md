# PART 0 — How to hand this to Antigravity

**Setup once, before the first task:**

```bash
git init
uv init --python 3.12 --lib
```

**Then feed phases one at a time.** Never dump all 17 phases into one prompt — the agent will hallucinate an entire codebase and it will be broken.

**The per-phase loop Antigravity must follow:**

1. Read `docs/SPEC.md` (this doc) + `docs/CONTRACTS.md` + `AGENTS.md`
2. Read the phase section only
3. Write failing tests first for anything with a deterministic output (parsers, resolvers, FSM)
4. Implement
5. Run `make gate` — must exit 0
6. Run the phase acceptance gate
7. `git commit` with `feat(P<n>): ...`
8. Report: files touched, tests added, gate output, blockers

**Five hard rules for the human:**

| Rule | Why |
|---|---|
| Never let it modify `contracts/` after P1 without a version bump | Every other module depends on those shapes |
| Never let it run tools against the host during unit tests | Non-reproducible, slow, needs root |
| Require a golden fixture for every parser | Tools change output formats; fixtures are your regression net |
| One phase per session, review before continuing | Broken P4 makes P5–P16 garbage |
| If a gate fails twice, stop and fix manually | Agents loop forever on the same error |

---

# PART 1 — Locked architecture decisions

These are frozen. Antigravity must not "improve" them without asking.

| Area | Decision | Reason |
|---|---|---|
| Python | 3.12, `uv`, `src/` layout, full type hints | Speed, modern syntax |
| Schemas | Pydantic v2 everywhere, in `contracts/` | One source of truth |
| Persistence | SQLite in WAL mode, SQLModel, **event-sourced** | Zero-ops, replayable, auditable |
| Agent loop | **Hand-rolled deterministic FSM** (not LangGraph) | ~250 lines, fully testable, no dependency churn |
| Concurrency | `asyncio` + bounded worker pool | Tool orchestration is IO-bound |
| Tool execution | One `runner.py`, subprocess or Docker | Single choke point for scope/rate/risk |
| Event bus | In-process asyncio pub/sub (Redis added in P15) | Start simple |
| LLM | Provider-agnostic client, role-based model routing | Swap models freely |
| Frontend | React + Vite + TS, FastAPI + WebSocket backend | Streaming UI needs real WebSockets |
| Reports | Jinja2 → HTML → WeasyPrint PDF | Deterministic, offline |
| Testing | pytest, golden fixtures, docker-compose lab | Hermetic |
| Packaging | `pipx installable` CLI + `systemd` unit for the watch daemon | Real deployment |

**The one rule that defines the whole project:**

> Raw tool output NEVER enters LLM context. Parsers convert it to `Fact` objects first. The planner reasons over a compact graph render (target ≤ 4KB per decision).

---

# PART 2 — Repo skeleton

```
venice-pt/
├── AGENTS.md
├── Makefile
├── pyproject.toml
├── docs/
│   ├── SPEC.md              # this document
│   ├── CONTRACTS.md         # generated from contracts/ docstrings
│   ├── ARCHITECTURE.md
│   └── RUNBOOK.md
├── src/venice_pt/
│   ├── __init__.py
│   ├── cli.py                      # typer entrypoint
│   ├── config.py                   # pydantic-settings, ~/.venicept/config.toml
│   ├── logging.py                  # structlog setup
│   ├── contracts/                  # FROZEN after P1
│   │   ├── events.py
│   │   ├── tools.py
│   │   ├── facts.py
│   │   ├── decisions.py
│   │   ├── findings.py
│   │   └── llm.py
│   ├── store/
│   │   ├── db.py                   # engine, migrations
│   │   ├── eventlog.py             # append-only, immutable
│   │   ├── bus.py                  # async pub/sub
│   │   └── projections.py          # read models for UI
│   ├── registry/
│   │   ├── schema.py
│   │   ├── loader.py
│   │   └── tools/*.yaml            # one per tool
│   ├── bootstrap/
│   │   ├── distro.py
│   │   ├── resolver.py
│   │   ├── docker.py
│   │   ├── lockfile.py
│   │   └── doctor.py
│   ├── exec/
│   │   ├── sandbox.py
│   │   ├── runner.py               # THE only subprocess caller
│   │   ├── flags.py                # --help → schema → validation
│   │   ├── scope.py                # allowlist enforcement
│   │   └── ratelimit.py
│   ├── parsers/
│   │   ├── base.py                 # Parser protocol + registry
│   │   ├── nmap.py  httpx.py  nuclei.py  ffuf.py  sqlmap.py  ...
│   │   └── _registry.py
│   ├── knowledge/
│   │   ├── models.py
│   │   ├── graph.py                # traversal + queries
│   │   ├── render.py               # compact LLM render
│   │   └── rag.py                  # CVE/advisory embeddings
│   ├── brain/
│   │   ├── fsm.py                  # phase state machine
│   │   ├── checkpoint.py
│   │   ├── planner.py
│   │   ├── interpreter.py
│   │   ├── router.py               # phase→tool selection policy
│   │   ├── budget.py               # cost governor
│   │   └── prompts/*.jinja
│   ├── verify/
│   │   ├── verifier.py
│   │   └── rules/*.py              # per-finding-class confirmers
│   ├── novel/
│   │   ├── oracle.py  payloads.py  diff.py  callbacks.py  chains.py
│   ├── report/
│   │   ├── render.py  scoring.py  templates/
│   ├── server/
│   │   ├── app.py  ws.py  auth.py  routes/
│   ├── watch/
│   │   ├── scheduler.py  drift.py  cve_match.py  logs.py  alerts.py
│   └── cli/
│       ├── init.py  doctor.py  run.py  serve.py  watch.py  replay.py  report.py
├── ui/                              # React + Vite
├── lab/                             # docker-compose vulnerable targets
│   ├── docker-compose.yml
│   └── targets/                     # juice-shop, dvwa, custom php app
├── tests/
│   ├── unit/  integration/  fixtures/<tool>/
└── engagements/                     # runtime output (gitignored)
```

---

# PART 3 — Frozen contracts

Antigravity implements these in **P1** and never changes them without a version bump. Everything else is built against them.

```python
# src/venice_pt/contracts/events.py
CONTRACT_VERSION = "1.0.0"

class Phase(StrEnum):
    SCOPE="scope"; RECON="recon"; ENUM="enum"; VULN_SCAN="vuln_scan"
    NOVEL_FUZZ="novel_fuzz"; VALIDATE="validate"; CHAIN="chain"; REPORT="report"

class Risk(IntEnum):
    PASSIVE=0; SAFE=1; INTRUSIVE=2; DESTRUCTIVE=3

class EventKind(StrEnum):
    ENGAGEMENT_START="engagement_start"; PHASE_ENTER="phase_enter"
    THOUGHT="thought"; PLAN="plan"; CMD="cmd"; STDOUT="stdout"; STDERR="stderr"
    FACT="fact"; FINDING="finding"; VERDICT="verdict"; APPROVAL_REQ="approval_req"
    APPROVAL_RES="approval_res"; ERROR="error"; ARTIFACT="artifact"
    METRIC="metric"; PHASE_EXIT="phase_exit"; ENGAGEMENT_END="engagement_end"

class Event(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=new_id)
    engagement_id: str
    ts: datetime = Field(default_factory=utcnow)
    phase: Phase
    actor: Literal["planner","runner","parser","verifier","reporter","human","system"]
    kind: EventKind
    tool: str | None = None
    cmd: str | None = None
    payload: dict = {}
    parent_id: str | None = None       # provenance chain
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    duration_ms: int = 0
```

```python
# src/venice_pt/contracts/tools.py
class OutputSpec(BaseModel):
    format: Literal["json","xml","csv","text","sarif"]
    parser: str                        # "venice_pt.parsers.nmap:parse"
    normalizes_to: list[str]

class InstallStep(BaseModel):
    method: Literal["apt","dnf","pacman","brew","pipx","go","cargo","github_release","docker","script"]
    pkg: str | None = None
    image: str | None = None
    entrypoint: str | None = None
    url: str | None = None
    script: str | None = None

class ToolSpec(BaseModel):
    name: str
    binary: str
    version_pin: str | None = None
    capabilities: list[str]
    phases: list[Phase]
    risk: Risk
    timeout_s: int = 300
    needs: list[str] = []              # cap_net_raw, docker, root
    install: list[InstallStep]
    check: str                         # "--version"
    output: OutputSpec
    cost_class: Literal["cheap","medium","heavy"] = "cheap"
    notes: str | None = None
```

```python
# src/venice_pt/contracts/facts.py
class FactKind(StrEnum):
    ASSET="asset"; PORT="port"; SERVICE="service"; TECHNOLOGY="technology"
    ENDPOINT="endpoint"; PARAM="param"; CREDENTIAL="credential"
    SECRET="secret"; VERSION="version"; HEADER="header"; CERT="cert"
    DNSRECORD="dns_record"; INTERESTING="interesting"

class Fact(BaseModel):
    kind: FactKind
    key: str                           # dedup key, e.g. "port:10.0.0.1:443/tcp"
    value: dict
    parent_key: str | None = None
    source_tool: str
    source_event: str
    confidence: float = Field(ge=0, le=1, default=1.0)
    tags: list[str] = []
```

```python
# src/venice_pt/contracts/decisions.py
class Action(StrEnum):
    RUN_TOOL="run_tool"; RUN_COMMAND="run_command"; QUERY_GRAPH="query_graph"
    ASK_HUMAN="ask_human"; ADVANCE_PHASE="advance_phase"; FINISH="finish"

class Decision(BaseModel):
    action: Action
    tool: str | None = None
    args: list[str] = []
    target: str | None = None
    rationale: str                     # shown in UI "why" pane
    hypothesis_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    risk: Risk
    expects: list[str] = []            # expected FactKinds, for scoring
    budget_hint_usd: float = 0.05
```

```python
# src/venice_pt/contracts/findings.py
class FindingOrigin(StrEnum):
    KNOWN_TOOL="known_tool"; CVE_MATCH="cve_match"
    NOVEL_ORACLE="novel_oracle"; LLM_HYPOTHESIS="llm_hypothesis"

class Finding(BaseModel):
    id: str = Field(default_factory=new_id)
    engagement_id: str
    title: str
    cls: str                           # sqli, xss, ssrf, misconfig, idor, race
    asset_key: str
    endpoint: str | None = None
    param: str | None = None
    severity: Severity
    cvss: float | None = None
    cvss_vector: str | None = None
    cwe: str | None = None
    owasp: str | None = None
    origin: FindingOrigin
    confidence: float
    verified: bool = False
    evidence: list[str] = []           # artifact paths
    repro: str | None = None           # exact curl / steps
    impact: str | None = None
    remediation: str | None = None
    chains_with: list[str] = []

class Verdict(BaseModel):
    finding_id: str
    confirmed: bool
    method: str
    evidence: list[str] = []
    confidence_delta: float = 0.0
    notes: str | None = None
```

```python
# src/venice_pt/contracts/llm.py
class LLMRole(StrEnum):
    TRIAGE="triage"; PLANNER="planner"; ANALYST="analyst"; REPORTER="reporter"

class LLMResult(BaseModel):
    text: str
    parsed: BaseModel | None = None
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int

class LLMClient(Protocol):
    async def complete(
        self, role: LLMRole, messages: list[Msg],
        schema: type[BaseModel] | None = None, max_tokens: int = 2048,
    ) -> LLMResult: ...
```

```python
# src/venice_pt/exec/runner.py  (signature contract)
class ToolResult(BaseModel):
    event_id: str
    tool: str
    argv: list[str]
    exit_code: int
    duration_s: float
    stdout_path: Path
    stderr_path: Path
    parsed: BaseModel | None
    facts: list[Fact]
    error: str | None = None

class Runner(Protocol):
    async def execute(self, spec: ToolSpec, args: list[str], *,
                      engagement_id: str, phase: Phase,
                      stdin: bytes | None = None) -> ToolResult: ...
```

---

# PART 4 — The phases

Each phase has a **Gate**: a single command that must pass. Antigravity may not proceed otherwise.

---

## P0 — Scaffold and conventions

**Goal:** empty repo that builds, lints, types, tests, and has a working CLI stub.

**Deliverables:** `pyproject.toml`, `Makefile`, `AGENTS.md`, `src/` tree with `__init__.py`s, `config.py`, `logging.py`, `cli.py` with `--version`.

**Makefile targets:** `setup`, `lint`, `typecheck`, `test`, `gate`, `lab-up`, `lab-down`, `test-int`, `doctor`, `fmt`.

**Gate:** `make gate` exits 0. `venice-pt --version` prints semver. `venice-pt --help` lists subcommands.

---

## P1 — Frozen contracts

**Goal:** all Pydantic models from PART 3, plus `docs/CONTRACTS.md` generated from them.

**Tasks:** implement every model, add `CONTRACT_VERSION`, write `tests/unit/contracts/test_roundtrip.py` (every model serializes/deserializes, every enum is stable), add a `contract_guard` test that hashes the contract modules and fails if they change without a version bump.

**Gate:** `make gate` passes; `docs/CONTRACTS.md` regenerates cleanly; contract hash test passes.

---

## P2 — Event store and bus

**Goal:** append-only event log + async pub/sub + read projections.

**Files:** `store/db.py`, `store/eventlog.py`, `store/bus.py`, `store/projections.py`.

**Tasks:**
- SQLite WAL, `events` table with indexes on `(engagement_id, ts)` and `parent_id`
- `EventLog.append(Event) -> Event` — never updates, never deletes
- `EventLog.walk_chain(event_id) -> list[Event]` — provenance ancestry
- `EventBus.publish` / `subscribe(engagement_id) -> AsyncIterator[Event]`
- `Projections`: `engagement_summary`, `phase_progress`, `findings_table`, `cost_meter` — pure functions over the log
- `replay.py`: rebuild any projection from event 0

**Tests:** append 10k events < 1s; chain walk correctness; projection determinism (same log → same output); bus fan-out to 3 subscribers.

**Gate:** `venice-pt replay --demo` reconstructs state; `make gate` passes.

---

## P3 — Tool registry and bootstrap resolver *(parallel with P2)*

**Goal:** `venice-pt doctor` on a clean machine installs everything and proves it.

**Files:** `registry/schema.py`, `registry/loader.py`, `registry/tools/*.yaml`, `bootstrap/*`.

**Tasks:**
- Manifest loader with strict validation (unknown keys = error)
- Distro detection: apt/dnf/pacman/brew + version
- `Resolver.ensure(capability)` walking the install fallback chain
- Native installs into `~/.venicept/toolchain/{bin,lib}` prepended to `PATH`; `sudo` only when required, streamed to events
- Docker fallback for `docker` method — `docker pull`, `docker run --rm`
- `lockfile.py` records `{tool, version, method, sha}` for reproducibility
- `doctor.py` prints a Rich table: capability → tool → status → version; `--json` flag
- **Start with 8 manifests only:** nmap, httpx, subfinder, nuclei, ffuf, katana, dnsx, whatweb

**Tests:** fake `shutil.which` to simulate missing tools; assert fallback ordering; assert lockfile written; assert second run is a no-op under 2s.

**Gate:** in a fresh `ubuntu:24.04` container, `venice-pt doctor` installs all 8 and exits 0. Running twice: no-op.

---

## P4 — Execution runner, sandbox, scope, rate limiting

**Goal:** the single choke point for running anything.

**Files:** `exec/runner.py`, `exec/sandbox.py`, `exec/flags.py`, `exec/scope.py`, `exec/ratelimit.py`.

**Tasks:**
- `Runner.execute()` — async subprocess, streamed stdout/stderr → events, hard timeout, kill on timeout, artifact files written to `engagements/<id>/artifacts/<event_id>.{out,err}`
- Docker mode: same interface, `--network host` where needed, no egress outside scope
- `scope.py`: parse scope file (domains, CIDRs, exclusions); every target validated before execution; violation → `ERROR` event, not a crash
- `ratelimit.py`: per-host token bucket from manifest defaults; `--delay`/`--rate` injected automatically
- `flags.py`: on first use of a tool, run `--help`, ask TRIAGE LLM to emit a flag schema, cache to `~/.venicept/flags/<tool>.json`. `validate_args(spec, args)` drops unknown flags and logs a warning
- Risk gate: `runner` refuses `risk > engagement.risk_ceiling` unless `--force`

**Tests:** timeout kills the process; scope violation blocked; unknown flag dropped; flag schema cached after one call; streamed events arrive in order.

**Gate:** `venice-pt exec --tool nmap --args "-sV -p 22,80" --target 127.0.0.1` produces events, artifacts, parsed `None`, exit 0.

---

## P5 — Parsers and knowledge graph

**Goal:** the understanding layer. **This is the highest-value phase — do not rush it.**

**Files:** `parsers/base.py`, `parsers/*.py`, `knowledge/models.py`, `knowledge/graph.py`, `knowledge/render.py`.

**Tasks:**
- `Parser` protocol: `parse(stdout: bytes, ctx) -> list[Fact]`
- Implement parsers for the P3 tools + `tests/fixtures/<tool>/*.{json,xml,txt}` captured from real runs (Antigravity must run the tools once against `lab/` and commit real output)
- Graph: nodes = `Fact.key`, edges = `parent_key`; helpers `children`, `subtree`, `by_kind`, `merge_duplicates`
- `render.py`: compact text render for LLM — target **≤ 4KB**, truncating low-value facts first, always including: open services, technologies+versions, endpoints count, top 20 interesting endpoints, confirmed findings
- `unexplored_surface()`: computes what hasn't been probed yet — this is the planner's main input

**Tests:** every parser has a golden fixture test; graph dedup (same port from two tools = one node, merged confidence); render stays under 4KB with 5000 facts.

**Gate:** run nmap+httpx+nuclei against `lab/juice-shop`; ≥ 40 facts produced across ≥ 4 kinds; render ≤ 4KB; zero duplicate keys.

---

## P6 — CLI and engagement lifecycle

**Goal:** real usable tool from the terminal.

**Commands:** `init`, `doctor`, `run`, `status`, `replay`, `report`, `serve`, `watch`, `scope`, `tools`.

**Tasks:** `~/.venicept/config.toml` via pydantic-settings; engagement dirs `engagements/<slug>/` with `scope.yaml`, `events.db`, `artifacts/`, `state.json`; `run --target X --profile web --risk safe --budget 5` starts an engagement; graceful Ctrl-C → checkpoint; `status` shows live progress via Rich.

**Gate:** `venice-pt init && venice-pt run --target http://localhost:3000 --phases recon,enum` completes and writes findings to the graph. Ctrl-C mid-run then `run --resume` continues.

---

## P7 — Planner FSM (deterministic rails)

**Goal:** the pentest always completes, LLM or not.

**Files:** `brain/fsm.py`, `brain/checkpoint.py`, `brain/router.py`.

**Tasks:**
- `PhaseState` with entry/exit conditions per phase; phases: SCOPE→RECON→ENUM→VULN_SCAN→NOVEL_FUZZ→VALIDATE→CHAIN→REPORT
- `router.py`: static policy — capability list required per phase; picks the cheapest tool satisfying each capability not yet run against each target
- Loop guard: max iterations per phase, max total tool calls, no-progress detector (if 3 consecutive runs yield 0 new facts → advance)
- `checkpoint.py`: persist `PhaseState` + graph cursor after every event; resume from any point
- Rule-based fallback mode: `--no-llm` runs the whole FSM on static policy

**Tests:** FSM reaches REPORT with LLM stubbed out; loop guard fires; no-progress detector advances; checkpoint/resume byte-identical state.

**Gate:** `venice-pt run --no-llm --target http://localhost:3000` produces a complete run with findings and a stub report. **This gate is the project's backbone.**

---

## P8 — LLM layer, planner intelligence, budget governor

**Goal:** add judgment on top of the rails.

**Files:** `brain/planner.py`, `brain/interpreter.py`, `brain/budget.py`, `brain/prompts/*.jinja`.

**Tasks:**
- `LLMClient` implementation (OpenAI-compatible; works with Venice/Ollama/anything). Retries with backoff, JSON-mode + schema validation, `parsed` via Pydantic
- Role routing table in config: `triage → cheap`, `planner → mid`, `analyst → strong`, `reporter → strong`; per-role max tokens
- `planner.plan(state) -> list[Decision]`: input = compact graph render + unexplored surface + available tools (name, capabilities, risk) + budget + risk ceiling. Output = **validated JSON** matching `Decision`
- `interpreter.interpret(tool_result, state) -> Interpretation`: summarises output into facts + hypotheses + "what this means"
- `budget.py`: hard cap, per-role spend tracking, downgrade-to-cheap-model when >80% consumed, `BudgetExceeded` → advance to REPORT
- Every LLM call emits `THOUGHT`/`PLAN` events with `parent_id` linking to the triggering fact

**Tests:** planner output validates against schema with a mocked LLM; malformed JSON → repair retry then fallback to static router; budget cap halts; model downgrade triggers at threshold.

**Gate:** `venice-pt run --target http://localhost:3000 --budget 2` finds ≥ 3 findings the `--no-llm` run missed. Cost ≤ $2.

---

## P9 — Verification layer

**Goal:** kill false positives before they reach the report.

**Files:** `verify/verifier.py`, `verify/rules/*.py`.

**Tasks:**
- `Verifier.check(finding) -> Verdict` dispatching per class
- Independent re-production: fresh requests, fresh evidence, no reuse of the discovering tool's output
- `cve_match` findings → reachability test (does the endpoint respond as the vuln requires?)
- `llm_hypothesis` → must survive a second, differently-constructed test
- Confirmation must use a **different oracle** than discovery (reflection→browser execution; timing→value extraction; OOB→callback correlation)
- Unconfirmed → `confidence *= 0.4`, moved to appendix
- Findings table gets `verified` + evidence bundle

**Tests:** known-FP corpus (10 planted false positives) → all demoted; known-TP corpus → all confirmed.

**Gate:** 0 verified findings in the lab that can't be reproduced by a hand-written curl.

---

## P10 — Report generator *(parallel with P11)*

**Deliverables:** `report/render.py`, `report/scoring.py`, `report/templates/*.jinja`.

**Structure:** cover → exec summary → scope & methodology → risk matrix → findings (title, severity, CVSS 3.1 via `cvss` lib, CWE, OWASP, affected asset, description, evidence, exact repro, impact, remediation with code snippets, references) → attack chains → appendix A raw tool output, appendix B timeline, appendix C unconfirmed findings, appendix D tool/version inventory.

**Outputs:** `report.html`, `report.pdf` (WeasyPrint), `findings.json` (SARIF-compatible), `findings.csv`.

**Gate:** lab engagement produces a PDF that opens, with all verified findings, correct CVSS maths, and no template errors.

---

## P11 — API and WebSocket backend *(parallel with P7–P10)*

**Files:** `server/app.py`, `server/ws.py`, `server/auth.py`, `server/routes/*`.

**Routes:** `GET /api/engagements`, `GET /api/engagements/{id}`, `GET /api/engagements/{id}/events?since=`, `GET /api/engagements/{id}/chain/{event_id}`, `GET /api/findings`, `POST /api/engagements/{id}/control` (pause/resume/abort/guidance/risk), `POST /api/approvals/{id}`, `WS /ws/engagements/{id}`.

**WS protocol:** server → client `{type:"event", data:Event}`; client → server `{type:"control", action:...}`. Reconnect with `since=<last_event_id>` for gap-free resume.

**Gate:** `venice-pt serve` then a Python test client connects over WS, receives live events from a running engagement, sends pause, and the engagement pauses.

---

## P12 — Dashboard frontend *(parallel with P13–P15)*

**Stack:** React + Vite + TS + Tailwind. Build the mockup from earlier as the real thing.

**Views:** live stream (virtualised, filter, follow-tail), phase rail, attack graph (D3 force/elk, clickable → evidence), findings table → detail drawer, reasoning pane, cost meter, tool status, approval queue, artifact browser, report preview, replay scrubber.

**Non-negotiables:** reconnect-resume via `since`, virtualised list (10k+ events), keyboard shortcuts, works at 1280px, dark/light.

**Gate:** run a live engagement; the UI streams events within 1s, pause works, clicking a command shows its full provenance chain.

---

## P13 — Novel oracle engine and callbacks

**Goal:** find bugs no template covers.

**Files:** `novel/oracle.py`, `novel/payloads.py`, `novel/diff.py`, `novel/callbacks.py`.

**Tasks:**
- `Baseline` capture per endpoint (status, length, hash, timing, headers, JSON shape, error signatures)
- `Delta` computation + `interesting()` heuristic thresholds
- Payload classes: sqli_bool, sqli_time, sqli_error, xss_reflect, ssti, pathtraversal, cmdi, ssrf, xxe, nosql, ldap, prototype_pollution, crlf, host_header, open_redirect
- `payloads.py`: LLM synthesis given (tech stack, param name, observed errors) → 5–15 targeted payloads, executed, scored
- `callbacks.py`: self-hosted DNS+HTTP listener; register nonce per probe; correlate OOB hits to probes; `--callback-domain` config
- Candidates → `Finding(origin=NOVEL_ORACLE, confidence=0.5)` → **must pass P9 verification**
- Dedup against known-tool findings to isolate genuinely novel results

**Tests:** against lab targets with known bugs: time-based SQLi detected with 0 FPs over 200 clean params; OOB SSRF detected; `--help`-level robustness (no crash on binary bodies).

**Gate:** lab run detects ≥ 3 bugs that nuclei's full template set misses, with zero false positives.

---

## P14 — Chain planner and logic testing

**Files:** `novel/chains.py`, `novel/logic/{idor,race,jwt,graphql,massassign}.py`.

**Tasks:** IDOR enumeration + authz diffing; race harness (N parallel requests, double-spend detection); JWT attacks (alg confusion, none, weak HMAC, kid injection); GraphQL introspection + alias batching + depth; mass assignment probing. `chains.py`: BFS over confirmed primitives, scoring chains by combined impact, emitting `Finding(origin=LLM_HYPOTHESIS)` for confirmed compositions.

**Gate:** lab run produces ≥ 1 verified multi-step chain with a reproducible PoC.

---

## P15 — 24/7 watch service

**Files:** `watch/*`.

**Tasks:**
- APScheduler jobs: passive watch 15m, light sweep 6h, CVE sync 1h, full audit weekly
- `drift.py`: snapshot (subdomains, ports, headers, TLS, cert, JS bundle hashes, endpoint list, tech versions) → diff → emit `DRIFT` events → only changed surface enters scanning
- `cve_match.py`: NVD/OSV/GitHub advisory mirror, semantic version ranges, reachability check, exploitability verdict
- `logs.py`: tail nginx/apache access+error logs, baseline, flag 404/500 spikes, traversal attempts, scanner UAs, per-IP floods
- `alerts.py`: webhook/Telegram/Slack/email; delta-only; dedupe + suppression windows
- `systemd/venice-pt-watch.service`
- Optional output: generated ModSecurity/Coraza rules + nginx/Cloudflare snippets from findings

**Gate:** add a target, inject a change (new subdomain + changed header + new endpoint), watch service alerts within one cycle with correct delta, and does not re-scan unchanged surface.

---

## P16 — Hardening, packaging, docs

**Tasks:** `pipx`-installable; Docker image; `RUNBOOK.md`; config reference; upgrade/migration path for the event DB; scope-allowlist fuzz test; crash-resume fuzz test; secrets in keyring/`age`; signed audit log; `--dry-run`; performance pass (10k events, 500 findings → UI under 2s); coverage ≥ 75% on `contracts/`, `exec/`, `knowledge/`, `brain/`.

**Gate:** fresh machine → `pipx install` → `venice-pt doctor` → `venice-pt run` against a real external target → PDF report. No manual steps.

---

# PART 5 — Tool catalogue by phase

Add manifests in this order. Each needs manifest + parser + fixture + test.

| Phase | Tools |
|---|---|
| RECON | subfinder, amass, dnsx, tlsx, httpx, naabu, nmap, masscan, whatweb, wafw00f |
| ENUM | katana, gau, waybackurls, ffuf, feroxbuster, gobuster, arjun, x8 |
| VULN_SCAN | nuclei, nikto, testssl.sh, sslyze, semgrep, trivy |
| Secrets | trufflehog, gitleaks |
| Callbacks | interactsh-client |
| Validation | sqlmap, dalfox, commix, corsy |
| GraphQL/JWT | graphql-cop, clairvoyance, jwt_tool |
| Creds | hydra, john, hashcat, netexec, impacket, kerbrute, smbmap, enum4linux-ng |
| Exploit | metasploit (docker + pymetasploit3), searchsploit |
| Screenshots | playwright |
| Binary | afl++, honggfuzz, gdb |

---

# PART 6 — Test strategy

| Layer | Approach |
|---|---|
| Unit | Pure functions, no network. Fixtures for all parser inputs. |
| Contract | Roundtrip + hash guard on `contracts/`. |
| Integration | `lab/docker-compose.yml` — juice-shop, dvwa, a custom PHP app with planted bugs, a small REST API with IDOR/race. Hermetic, deterministic. |
| Golden | Every parser: real tool output committed to `tests/fixtures/<tool>/`. Regenerate with `make fixtures`. |
| Regression | Known-FP and known-TP corpora for the verifier. |
| Resilience | Kill mid-run → resume. Malformed tool output → no crash. LLM returns garbage → fallback to static router. |
| E2E | `make test-e2e` — full engagement against lab, assert findings ≥ N, report exists, budget respected. |

**Never** run tools against the internet in unit tests. **Never** require root in CI.

---

# PART 7 — `AGENTS.md` (paste verbatim)

```markdown
# AGENTS.md

## Project
venice-pt — autonomous AI pentest platform. Linux only. Python 3.12.

## Commands
- `make setup`     install dev deps
- `make gate`      lint + typecheck + unit tests — MUST pass before every commit
- `make lab-up`    start local vulnerable targets
- `make test-int`  integration tests against lab
- `make doctor`    verify toolchain

## Hard rules
1. Python 3.12. Type hints on every public function. `from __future__ import annotations`.
2. `mypy --strict` on `contracts/`, `exec/`, `knowledge/`, `brain/`.
3. Subprocess is called ONLY from `exec/runner.py`. Nowhere else.
4. Any data crossing a module boundary MUST be a Pydantic model from `contracts/`.
5. Never change `contracts/` without bumping `CONTRACT_VERSION` and updating `docs/CONTRACTS.md`.
6. Every new tool requires: manifest YAML + parser + golden fixture + unit test.
7. Never write outside `~/.venicept/` and `engagements/`.
8. Unit tests: no network, no root, no real tool execution.
9. Log with structlog. Never `print()` outside `cli/`.
10. Raw tool output NEVER goes into LLM context — only `knowledge/render.py` output.
11. LLM-generated commands MUST be validated against the cached flag schema before execution.
12. Every long operation is checkpointed. Crash must be resumable.
13. No new dependency without adding it to `pyproject.toml` and justifying it in the commit body.
14. If a test fails twice in a row, stop and report — do not loop.

## Workflow
Read `docs/SPEC.md` + `docs/CONTRACTS.md` + the current phase section.
Tests first for deterministic components. Implement. `make gate`. Phase gate. Commit `feat(P<n>): ...`. Report.

## Phase report format
- Phase: P<n>
- Files created/modified
- Tests added (names + what they assert)
- `make gate` output
- Phase gate result
- Blockers / deviations from spec
```

---

# PART 8 — Ready-to-paste Antigravity prompts

**Kickoff:**

```
Read AGENTS.md, docs/SPEC.md (PART 2 and PART 3), and docs/CONTRACTS.md.
Execute P0 only: scaffold the repo exactly as specified in SPEC PART 2.
Create every directory, __init__.py, pyproject.toml, Makefile, AGENTS.md.
Add a typer CLI with --version and --help, structlog setup, and pydantic-settings config.
Write tests that assert `make gate` passes and the CLI works.
Do not implement anything from P1 or later. Stop when the P0 gate passes.
```

**Per phase (substitute N):**

```
Phase P<N>. Read the P<N> section of docs/SPEC.md.
Implement only that phase. Follow AGENTS.md rules exactly.
For deterministic components write failing tests first.
Run `make gate` and the P<N> gate. Iterate until both pass.
Do not start P<N+1>.
Report in the AGENTS.md phase report format.
```

**Debug prompt:**

```
Gate for P<N> fails. Here is the exact output: <paste>.
Diagnose the root cause before changing code. Propose one fix, apply it, re-run the gate.
If it fails again, stop and report rather than trying a third approach.
```

---

# PART 9 — Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| Agent dumps raw output into LLM → cost explosion | High | Enforce `render.py` boundary; assert ≤ 4KB in a test |
| Parsers silently break on tool updates | High | Version pins + golden fixtures + `make fixtures` |
| LLM hallucinates CLI flags | High | P4 flag-schema cache + validation before execution |
| Agent "improves" contracts mid-build | Medium | Contract hash guard test |
| Endless loops in the FSM | Medium | Max iterations, no-progress detector, budget cap |
| Scope violation on real targets | Medium | Scope check inside `runner`, before every execution |
| Destructive exploit on prod | Medium | Risk ceiling + approval gates at `DESTRUCTIVE` |
| 6-hour run dies at hour 5 | Medium | Checkpoint every event, `--resume` |
| False positives destroy trust | High | P9 mandatory; FP corpus regression test |
| Overreach — agent builds all 17 phases in one go | High | Strict one-phase-per-session rule |