# Runtime Guard adversarial review

Reviewed against `RUNTIME_GUARD_DESIGN.md`. Status: design hardening only, no runtime enforcement is implemented.

## Findings closed in the design contract

### RG-01: policy freshness and rollback

A correctly signed but stale policy can reopen destinations or capabilities. Every enforcement policy must bind artifact digest, monotonically increasing policy epoch, deployment identity and expiry. The broker persists the highest accepted epoch in rollback-resistant storage. Lower, expired, wrong-deployment or wrong-artifact policies fail closed. Wall-clock time alone is not an anti-rollback control.

### RG-02: decision and use race

A connection can change identity between authorization and use through DNS rebinding, proxy redirects, descriptor replacement or process handoff. Authorization binds the resolved endpoint set, protocol, socket identity, process identity and policy epoch. Redirects and endpoint changes require a new decision. Existing connections are re-evaluated when policy enters quarantine.

### RG-03: incomplete egress inventory

TCP port filtering does not cover UDP/QUIC, raw sockets, ICMP, DNS, Unix sockets, named pipes, inherited descriptors, shared memory, clipboard, files later uploaded by another process or child processes. Deployment policy declares required mediation surfaces. An adapter that cannot mediate any required surface refuses startup; unsupported surfaces are explicit residual risks, never silently treated as covered.

### RG-04: broker and alert compromise

The protected process must not share mutable trust state or signing authority with the broker. Control messages are authenticated, replay-protected and bound to an incident epoch. Alert loss cannot release or weaken quarantine. Alerts queue in a bounded local journal; overflow preserves a stable aggregate alarm without retaining secret payloads.

### RG-05: quarantine race and partial failure

Quarantine is deny-first: revoke new capability issuance, block new egress, re-evaluate or close covered existing channels, then freeze high-risk tool calls. Partial adapter failure moves to `FAIL_SAFE` for required controls. Physical-control deployments use a separately reviewed safe-state policy; blindly killing a process is forbidden when termination could cause harm.

### RG-06: detector evasion and poisoning

Low-and-slow exfiltration, distributed destinations, decoys and adversarial traffic can evade or poison anomaly thresholds. Deterministic policy violations block independently of anomaly scoring. Heuristics may escalate to suspicion but cannot grant access, declassify data or release quarantine. Threshold changes are versioned policy changes.

### RG-07: identity ambiguity

Path, filename, PID and process name are not artifact identity. Decisions bind a measured executable digest plus deployment identity and, where supported, verified launch ancestry. Dynamic libraries, plugins and injected code remain separate measurements or explicit assumptions.

### RG-08: telemetry as exfiltration

Diagnostics, DNS names, URLs, stack traces and sampled payloads can contain secrets. Event schemas use stable reason codes and allowlisted bounded fields. Untrusted values are hashed or redacted before journaling and transport. Payload capture is disabled by default and cannot be enabled by the protected process.

## Explicitly unclosed classes

The first implementation will not claim complete mediation of covert channels, malicious kernels/hypervisors, compromised hardware, unmeasured DMA, electromagnetic/acoustic channels or plaintext hidden inside end-to-end encrypted application protocols without an instrumented application boundary. These remain visible residual risks and candidates for future independently reviewed layers.

## Acceptance gates for an implementation PR

1. A machine-readable capability decision model with deny-by-default unknown fields and versions.
2. Deterministic state-machine tests including duplicate, reordered, delayed and replayed controls.
3. Fault injection for broker crash, adapter crash, alert outage, journal exhaustion and restart.
4. Endpoint identity tests covering DNS rebinding, IPv4/IPv6 aliases, redirects, proxies and inherited sockets.
5. Mediation inventory tests for every surface claimed by each platform adapter.
6. Quarantine concurrency tests proving no new covered egress after the deny transition.
7. Privacy tests proving alerts and logs do not echo marked secret fixtures.
8. Linux, Windows and macOS native integration tests with no skip for required controls.
9. Long-running low-and-slow and detector-poisoning scenarios.
10. Independent exact-head review before any claim stronger than “design” or “prototype”.

This list is a floor. Every new bypass adds a neighboring mutation family and a permanent regression.
