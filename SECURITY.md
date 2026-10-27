# Security Policy

## 1. Scope and Authorized Usage

> [!WARNING]
> `AIP_SAK` is an autonomous AI-driven penetration testing platform engineered specifically for **authorized security assessments, defensive research, internal auditing, and controlled lab evaluation**.
>
> Executing intrusive scans, exploitation workflows, or payload fuzzing against assets, networks, or endpoints without explicit, documented permission from the asset owner is illegal and strictly prohibited.

The maintainers and contributors assume no liability for misuse, unauthorized activities, or collateral damages resulting from the execution of `AIP_SAK`.

---

## 2. Hardened Architecture & Safe Execution Guarantees

`AIP_SAK` enforces defense-in-depth safety controls by design:

1. **Deterministic Choke Point (`exec/runner.py`)**: Subprocess execution is strictly centralized in a single module. No auxiliary library, LLM agent, or tool parser can spawn independent system processes.
2. **Strict Scope Allowlisting (`exec/scope.py`)**: Every target domain, IPv4, IPv6, or CIDR block is verified against the signed `scope.yaml` prior to process invocation. Out-of-scope targets are intercepted and blocked immediately.
3. **Adaptive Token-Bucket Rate Limiting (`exec/ratelimit.py`)**: Requests and tool invocations adhere to strict queries-per-second (QPS) thresholds to prevent denial-of-service (DoS) on operational infrastructure.
4. **Tool Flag Caching & Schema Validation (`exec/flags.py`)**: LLM-synthesized commands are pre-validated against authorized tool schemas before execution to prevent command injection or unauthorized flag tampering.
5. **Independent Verification Oracles (`verify/`)**: Candidate vulnerabilities undergo differential re-probing before confirmation. Unverified findings have confidence scores multiplied by `0.4` to eliminate false positives.

---

## 3. Reporting a Security Vulnerability

We treat the security of `venice-pt` with the highest priority. If you discover a security flaw, sandbox escape, scope bypass, or vulnerability within the platform, please disclose it responsibly.

### Disclosure Process
- **Do NOT file a public issue** on GitHub.
- Submit a detailed vulnerability report via encrypted email to:
  `security@venice-pt.internal` or via our coordinated disclosure portal.
- Include:
  - Description of the vulnerability and attack vector.
  - Step-by-step reproduction instructions or Proof of Concept (PoC).
  - Affected components (`exec/`, `server/`, `contracts/`, `watch/`).
  - Potential impact and suggested mitigations.

### Response Timeline
- **Initial Acknowledgment**: Within 24 hours.
- **Triage & Assessment**: Within 72 hours.
- **Patch Release & Public Advisory**: Coordinated within 30 days of initial triage.
