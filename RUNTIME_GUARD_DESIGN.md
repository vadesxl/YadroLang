# Yadro Runtime Guard: layered containment design

Статус: архитектурный контракт будущего companion-компонента. В 2.1.0 не реализован и не является свойством компилятора.

## Цель

Свести к минимуму вероятность и масштаб утечки чувствительных данных после компиляции. Compile-time Ethical Checker остаётся первым барьером; Runtime Guard добавляет независимое наблюдение и containment для поведения, которое статический анализ не видит: скомпрометированные зависимости, ошибочные внешние реализации, динамические endpoints и атаки после запуска.

Целевая безопасность не имеет фиксированного потолка: после каждого воспроизводимого обхода threat model, mutation corpus и enforcement расширяются. Публичный claim всегда ограничивается доказанными сценариями на текущей версии.

## Архитектура

```text
Yadro source -> Ethical Checker -> verified LLVM/object -> Proof Seal
                                                        |
                                              signed policy bundle
                                                        |
process -> capability broker -> egress mediator -> network
                  |                 |
             audit events       quarantine controller
                  |                 |
             local journal -> owner alert channel
```

Runtime Guard является отдельным минимальным privileged-компонентом. Компилятор не получает сетевые привилегии и не превращается в EDR.

## Enforcement layers

1. **Capability broker**: процесс получает только заранее разрешённые ресурсы, destinations, protocols и time windows. Неизвестная capability fail-closed.
2. **Egress mediator**: все поддерживаемые outbound connections сопоставляются с policy tuple `(binary identity, destination identity, protocol, purpose, data labels)` до разрешения.
3. **Label continuity**: runtime events ссылаются на versioned semantic labels и exact artifact identity. Потеря или несовместимость label metadata считается подозрением, а не разрешением.
4. **Port exposure policy**: listening sockets запрещены по умолчанию; открытие порта требует явной inbound capability, bind address, protocol и bounded lifetime. Проверяется фактический socket state, а не только конфигурация.
5. **Scan detection**: bounded rate/dispersion detectors выявляют fan-out, sequential port probing, destination churn и repeated denied attempts. Детектор не запускает встречное сканирование и не атакует источник.
6. **Quarantine**: deny new egress, revoke runtime capabilities, freeze high-risk tool calls and preserve bounded evidence. Process termination is a separate policy action because abrupt termination can itself endanger physical systems.
7. **Owner alert**: authenticated local-first event with monotonic sequence, artifact digest, policy version, reason code and redacted context. Raw secrets and payloads are excluded by default.
8. **Recovery**: release from quarantine requires authenticated policy decision, not a process-controlled flag.

## Platform adapters

- Linux: cgroup/network namespace plus supported kernel telemetry such as eBPF, with capability and kernel-version checks.
- Windows: Windows Filtering Platform and job/token isolation.
- macOS: Network Extension/Endpoint Security where entitlements permit.

Platform adapters must implement the same normative event and decision model. Missing enforcement support is a hard startup failure for a policy that requires it, never a silent downgrade.

## Ethical decision contract

Safety policy is represented as machine-checkable invariants, not a free-form claim that software understands universal morality.

- Human life, bodily integrity and fundamental rights are non-fungible protected interests.
- A high-level goal cannot silently declassify a protected interest or authorize sacrificing an identified person.
- When all known plans violate a hard invariant, the planner must search bounded alternative plans, request authenticated human escalation, and enter a defined safe state.
- The search bound, safe state and escalation deadline are domain-specific and verified before deployment.
- Inaction is modeled as an action with consequences; it cannot bypass policy evaluation.
- Emergency override, if a domain legally requires one, is external, multi-party, time-bounded, logged and outside autonomous model authority.

This contract does not solve every moral dilemma. It prevents an optimizer from converting protected interests into an unreviewed scalar trade-off.

## Quarantine state machine

```text
NORMAL -> SUSPECT -> QUARANTINED -> RECOVERY_PENDING -> NORMAL
   |          |             |
   +----------+-------------+-> FAIL_SAFE
```

Transitions are monotonic within an incident epoch. Untrusted code cannot move to a less restrictive state. Duplicate or reordered control messages do not release quarantine.

## Evidence and privacy

Every decision records stable reason codes, policy/artifact digests, monotonic counters and bounded metadata. Events are hash-chained locally; authenticated transport is a later independent layer. Logs must not become a second exfiltration channel: payload capture is opt-in, bounded, encrypted and label-aware.

## Required adversarial tests before implementation claims

- direct socket and alternate-library bypass attempts;
- DNS rebinding, IPv4/IPv6 representation tricks and proxy tunneling;
- localhost, Unix sockets, named pipes and inherited descriptors;
- fragmented/chunked payloads and low-and-slow exfiltration;
- process fork/exec, child injection and descriptor passing;
- policy downgrade, replay, clock rollback and event reordering;
- alert-channel outage and disk exhaustion;
- quarantine races with concurrent connections;
- false-positive recovery without leaking queued data;
- platform parity across Linux, Windows and macOS;
- crash/restart persistence and fail-safe startup;
- telemetry payload redaction and bounded memory/disk use.

The corpus grows after every discovered class. Passing this list alone is not a completeness claim.

## Non-goals of the first implementation

No counter-scanning, exploitation, retaliation or autonomous offensive action. No claim of visibility into encrypted plaintext without an explicit application boundary. No claim that port monitoring alone prevents data loss. No production-readiness claim before independent review, fault injection and long-running platform tests.
