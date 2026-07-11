# Печать Ядра: implementation map

Статус: план после принятия [нормативного дизайна](PROOF_SEAL.md). Этот файл не объявляет команды реализованными.

## Existing evidence inventory

- `src/этика_v21.py`: bounded interprocedural return/leak summaries, PC labels, sanitizer audit entries and mandate checks. Current `ЗаписьАудита` is human/audit oriented and insufficient as proof schema.
- `src/guard_impl.py`: invocation-local custom policy application, JSON/SARIF diagnostics and exit classes. Current policy mutation is process-global during invocation and must not be read directly by proof serializer.
- `src/mcp_guard_v2.py`: bounded deterministic tool graph, sorted findings, roots and fixpoint update count. Its summary can feed a separate typed MCP evidence adapter.
- `src/кодоген_verified.py`: verified LLVM text and stable ABI symbols.
- `src/main.py`: native emission and platform-specific COFF path. Proof finalization belongs after successful object write, not inside CodeGen.

## Required internal types

Create frozen immutable values in a new module, names subject to review:

```text
AnalysisEvidence
CallSiteEvidence
ExternalAssumption
FixpointEvidence
SubjectBinding
ProofSealCore
```

Fields use tuples, not mutable sets/lists. Constructors validate NFC, lengths, uniqueness and sorted canonical order. Serializer accepts only these values, never arbitrary dicts and never human audit strings.

## Ethical Checker changes

A future phase must:

1. retain caller function while traversing every effectful call;
2. compute reachable entry points over bounded call graph;
3. record source/callee/sink label state before and after sanitizer;
4. record mandate requirement and declaration;
5. expose fixpoint updates and bound;
6. emit assumptions for every external policy symbol;
7. return `(audit_trail, analysis_evidence)` without module-global evidence state.

Existing diagnostics remain authoritative for rejection. Evidence is created only after successful full check.

## Policy snapshot

Before analysis, build immutable effective policy snapshot from built-ins plus validated invocation-local additions. Hash canonical snapshot. Ethical Checker, semantic arity checks and evidence builder must consume the same snapshot object. This removes proof dependence on resettable module globals and prevents time-of-check/time-of-serialize drift.

## Source spans

Current AST mostly stores line numbers. Stable IDs require lexer/parser to retain UTF-8 byte start/end spans. Span work is a prerequisite and separate reviewed change. Until spans exist, Proof Seal must not fake stable identity from line number.

## LLVM normalization

Normalization adapter:

1. parse generated text with llvmlite;
2. verify module;
3. serialize through pinned compatibility version;
4. normalize CRLF/CR to LF;
5. require exactly one trailing LF;
6. hash bytes with domain separation if later versioned contract requires it.

No optimizer run is inserted merely for proof generation.

## Native binding and atomic output

Compiler flow returns verified IR and typed evidence. Native builder writes object first. Coordinator reads exact object bytes, computes digest, finalizes core, writes seal temp file in destination directory and atomically replaces regular non-symlink destination. Proof is absent on any failure.

Avoid exposing a generic callback between object emission and hashing. It would create a race and unclear trust boundary.

## Verifier modules

- bounded byte reader;
- duplicate-key rejecting JSON loader;
- strict structural validator independent of optional third-party schema package;
- NFC and semantic path validator;
- canonical serializer;
- digest verifier;
- deterministic renderer.

Verifier performs no import by user path, subprocess, network call or artifact execution.

## CLI phases

1. `proof inspect`: parse and display, explicitly unverified.
2. `proof verify`: structural and binding verification, explicit unsigned trust result.
3. `compile --emit-proof`: only after evidence and atomic output are complete.
4. optional future authenticated envelope verification.

Each phase gets subprocess CLI tests and installed-wheel smoke on Linux, macOS and Windows.

## Test modules

- `test_proof_canonical.py`: deterministic bytes, NFC, ordering, self-digest exclusion.
- `test_proof_parser_adversarial.py`: duplicate keys, depth, sizes, unknown fields, unsafe paths.
- `test_proof_binding.py`: artifact/policy/target mutation and swaps.
- `test_proof_evidence.py`: direct, sanitized, implicit and recursive flows, assumptions.
- `test_proof_native.py`: ELF/Mach-O/COFF compile, link-independent verify, no skip.
- `test_proof_cli.py`: exit classes, inspect vs verify wording and UTF-8 subprocesses.

## Benchmarks

Extend versioned benchmark output with independent metrics:

- `compile_without_proof`;
- `compile_with_proof`;
- `proof_serialize`;
- `proof_verify`;
- `proof_bytes` and `call_site_count`.

No threshold before repeated baseline data.
