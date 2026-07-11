# Архитектура

`source -> Lexer -> Parser/AST -> semantic checks -> type inference -> Ethical Analyzer -> LLVM CodeGen -> verified IR -> native object`

Продуктовые поверхности:
- `src.guard`: scan/compile/audit, custom JSON policy, JSON/SARIF.
- `src.mcp_guard`: статический анализ схемы Yadro MCP tool graph.

Этический анализатор использует конечную решётку, межпроцедурные сводки меток, PC labels и bounded fixpoints. LLVM ABI v1 нормализует bool в i64 на границах хранения/вызова/возврата и стабильно манглит символы.

## Planned: Печать Ядра

[Печать Ядра](PROOF_SEAL.md) проектируется как отдельный deterministic evidence artifact после успешного Ethical Checker, LLVM verification и native object emission. Она связывает policy, normalized LLVM и exact object bytes, перечисляет FFI assumptions и проверяется offline без исполнения artifact. Design не является реализованной CLI surface или formal proof всей программы.
