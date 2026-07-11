# Печать Ядра: market gap

Дата исследования: 2026-07-11. Это engineering comparison публично описанных возможностей, не сертификация vendors и не патентный поиск.

| Категория / пример | Основной control point | MCP | IFC / taint | Exact native artifact binding | Offline source-free verification | Explicit FFI assumptions |
|---|---|---:|---:|---:|---:|---:|
| Cisco MCP Scanner | server/config scan | да | частично | нет | нет | нет |
| MCP Firewall / MCP Visor | runtime gateway | да | policy dependent | нет | нет | нет |
| Lakera Agent Security | discovery/runtime protection | да | runtime context | нет | нет | нет |
| AgentPerms | observed behavior and runtime authorization | да | нет | нет | нет | нет |
| SAST / taint platforms | source/PR scan | varies | да | обычно нет | reports, не artifact proof | обычно нет |
| Sigstore / DSSE / SLSA attestations | supply-chain identity/provenance | agnostic | нет | да | да | нет semantic AI flow proof |
| PCAA / proof-derived authorization research | pre-action/runtime certificate | agnostic | contract dependent | иногда execution binding | да | model dependent |
| Yadro Proof Seal design | compile-time policy evidence | Yadro schema | да | LLVM + exact object | да | да |

## Вывод

Исследованная выборка хорошо покрывает scanning, runtime interception, software provenance и research action certificates по отдельности. Прямой продуктовый аналог, совмещающий compile-time capability/taint evidence, verified LLVM binding, exact native object binding, offline verification без source и explicit FFI assumptions, не найден.

## Позиционирование

Не говорить:

- «доказывает, что AI добрый»;
- «формально доказана вся программа»;
- «заменяет runtime security»;
- «единственное решение в мире».

Говорить:

- compile-time evidence для конкретного versioned policy contract;
- proof bound to exact emitted native artifact;
- auditable capabilities, data flows and external assumptions;
- offline deployment verification without executing artifact;
- no policy evaluation in application hot path.

## Публичные ориентиры

- Cisco AI Defense MCP Scanner: scan MCP servers for threats.
- MCP Firewall and MCP Visor: runtime policy gateway and audit.
- Lakera Agent Security: discovery and real-time agent protection.
- AgentPerms: observed behavior to least-privilege policy.
- Sigstore/DSSE/SLSA: standard supply-chain signing and provenance patterns.
- Research on proof-carrying agent actions, proof-derived authorization and information-flow control for agents.

Перед market claim для release нужен обновленный competitor review и legal/patent search.
