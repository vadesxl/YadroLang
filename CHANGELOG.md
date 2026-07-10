# Журнал изменений

## [2.1.0] - 2026-07-10

### Ethical Analyzer v2.1
- Межпроцедурные сводки с сохранением конкретных меток.
- Multi-label propagation, PC labels и bounded fixpoints.
- Деклассификация по меткам с записями САНИТАЙЗ.
- Защита source/sink/sanitizer от подмены и стабильные коды.
- Sound branch joins и loop-carried labels для zero-iteration loops.

### Компилятор и LLVM
- Вывод типов `ц64`, `булево` и ограниченной `строка`.
- Bool literals, mixed-type rejection, unreachable checks и recursive inference fixpoint.
- LLVM ABI v1 mangling, extern arity validation, terminator-safe blocks, bool normalization и verification каждого успешного IR.

### Продукт
- Installable команды `yadro-guard` и `yadro-guard-mcp`.
- scan/compile/audit/policy/version с изолированными custom policy.
- Text, JSON, SARIF 2.1.0 и стабильные exit codes.
- Сканер схемы Yadro MCP tool graph для sensitive flows и excessive agency.
- Threat model, specs, feature matrix, bounded fuzz corpus и измеренные benchmarks.

### Benchmarks
GitHub-hosted Ubuntu median: compile 1.3997 ms, Ethical Analyzer 0.1574 ms, MCP scan 0.3683 ms.

## [2.0.0] - 2026-07-10
Compiler hardening, reason-specific security regression tests, cross-platform CI, production audit и коммерческий roadmap.
