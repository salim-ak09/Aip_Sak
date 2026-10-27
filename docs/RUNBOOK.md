# venice-pt Operational Runbook

## 1. Quick Start

### Installation
```bash
# Development editable install
python -m pip install -e ".[dev]"

# Or production via pipx
pipx install .
```

### Environment Verification
Verify your toolchain and execution sandbox:
```bash
venice-pt doctor
```

---

## 2. Conducting Autonomous Engagements

### Initializing a Workspace
```bash
venice-pt init my-pentest --target https://target.internal
```
This generates:
- `engagements/my-pentest/scope.yaml`
- `engagements/my-pentest/events.db`
- `engagements/my-pentest/state.json`
- `engagements/my-pentest/artifacts/`

### Running the Autonomous Engine
```bash
# Safe passive/active scan with budget cap
venice-pt run --target https://target.internal --budget 2 --risk active

# Deterministic mode without external LLM calls
venice-pt run --target https://target.internal --no-llm
```

---

## 3. Reporting

Generate executive HTML, SARIF v2.1.0, and CSV reports:
```bash
venice-pt report --engagement my-pentest --format html,sarif,csv --output-dir ./reports
```

---

## 4. Serving the API & Dashboard

Start backend service:
```bash
venice-pt serve --host 0.0.0.0 --port 8000
```
Run React UI frontend:
```bash
cd ui && npm run dev
```

---

## 5. Continuous Attack Surface Watch

Run a single assessment cycle:
```bash
venice-pt watch --target 192.168.1.1 --once
```

Run continuous daemon:
```bash
venice-pt watch --target 192.168.1.1 --interval 3600
```
Or start systemd service:
```bash
sudo systemctl enable --now venice-pt-watch.service
```
