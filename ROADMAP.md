# Дорожная карта Yadro Guard после 2.1.0

Статус документа: инженерный план, не обещание готовых возможностей или сроков.

## Позиционирование

Yadro Guard проверяет конкретную версионированную policy до генерации нативного объекта и формирует аудируемое evidence в пределах реализованной семантики. Он не доказывает отсутствие всех утечек, не проверяет поведение произвольного внешнего кода и не заменяет runtime security.

## Уже реализовано в 2.1.0

- CLI `yadro-guard` с командами `scan`, `audit`, `compile` и проверкой JSON policy;
- JSON/SARIF diagnostics;
- capability mandates, multi-label taint и bounded interprocedural analysis;
- Yadro MCP tool-graph scanner;
- verified LLVM IR и native object emission;
- Linux, macOS и Windows CI;
- unsigned Proof Seal model и bounded library verifier.

Точный статус и ограничения находятся в [FEATURE_STATUS.md](FEATURE_STATUS.md), [THREAT_MODEL.md](THREAT_MODEL.md) и [PROOF_SEAL_IMPLEMENTATION.md](PROOF_SEAL_IMPLEMENTATION.md).

## Фаза A: закрыть текущие compiler gaps

- принять нормативную string memory model;
- реализовать `{ptr, i64}`, bounded printing и точную UTF-8 длину отдельным PR;
- завершить opt-in checked signed-i64 arithmetic;
- расширить fuzz/adversarial corpus Lexer, Parser, semantic analysis и CodeGen;
- сделать documentation examples исполняемыми в CI.

## Фаза B: интегрировать Proof Seal

- UTF-8 source byte spans;
- immutable effective policy snapshot;
- экспорт evidence из Ethical Checker;
- coverage/completeness invariants;
- versioned LLVM normalization;
- binding к exact native-object bytes;
- bounded ELF/Mach-O/COFF inspection;
- atomic proof output и CLI integration.

До завершения этой фазы unsigned Proof Seal подтверждает consistency записанного evidence, а не authenticity, provenance или полноту анализа.

## Фаза C: усилить доверие и parity

- стандартный authenticated envelope отдельным слоем;
- differential suite для русского и английского frontends;
- reproducible package artifacts;
- проверяемые framework adapters только после фиксации trust boundary;
- независимые exact-head security reviews и публикация residual risks.

## Долгосрочные критерии production readiness

Production readiness может быть заявлена только после документированной модели поддержки, воспроизводимых releases, supply-chain controls, fuzzing/coverage evidence, независимого аудита, стабильного ABI/diagnostics policy и закрытия известных high/critical findings. Текущий проект experimental.

## Коммерческая гипотеза

Целевая аудитория: AI platform engineering, AppSec и regulated product teams. Ценность должна подтверждаться воспроизводимыми blocked-attack scenarios, понятными false-positive/false-negative границами и evidence, которое можно независимо проверить. Pricing, SLA, SSO, retention и on-prem packaging пока не являются реализованными возможностями.

## Не делать ради видимости прогресса

Не клонировать Rust/C++, не расширять синтаксис без semantic необходимости, не выдавать дизайн за implementation и не публиковать security claim без теста или доказательства на текущем exact head.
