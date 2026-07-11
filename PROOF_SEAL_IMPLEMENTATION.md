# Печать Ядра: implementation status

## Phase 1 implemented

- frozen, slotted typed evidence model;
- canonical factories with duplicate rejection and UTF-8 ordering;
- NFC/type/hash/bounds/path/span validation;
- deterministic UTF-8 JSON serialization;
- domain-separated module and call-site IDs;
- content-addressed assumption IDs;
- unsigned seal self-digest;
- deterministic/adversarial tests and serialization benchmark.

## Phase 2 implemented in stacked PR

- 1 MiB bounded byte input and strict UTF-8/BOM rejection;
- non-recursive lexical depth scan before JSON parsing;
- nested duplicate-key rejection;
- bounded two-stage schema/policy/LLVM version preflight;
- explicit strict validators for every schema object;
- canonical ordering, uniqueness, span, fixpoint and reference checks;
- Phase 1 typed reconstruction;
- assumption content-ID verification;
- seal digest comparison with `hmac.compare_digest`;
- exact canonical-byte equality;
- deterministic `inspect_bytes` and `verify_bytes` results with unsigned trust state;
- stable `ЯДРО-П1xxx` diagnostics;
- deterministic mutation corpus;
- non-empty parse/verify benchmark fixture with 32 call sites and 8 assumptions.

`inspect_bytes` validates structure but does not verify digest or canonical bytes. `verify_bytes` verifies consistency only. Neither establishes authenticity.

## Existing integration inventory

- `src/этика_v21.py`: bounded summaries, PC labels, sanitizer audit and mandates. Current audit records are not proof evidence.
- `src/guard_impl.py`: invocation policy and diagnostics. Mutable runtime policy must become one immutable effective snapshot.
- `src/mcp_guard_v2.py`: bounded graph and fixpoint metadata, not yet seal evidence.
- `src/кодоген_verified.py`: verified LLVM and ABI symbols, not yet normalized or bound.
- `src/main.py`: native emission, not yet coordinated with proof output.

## Not implemented

- CLI commands or file-reading surface;
- Ethical Checker or MCP evidence export;
- UTF-8 source spans from Lexer/Parser;
- LLVM normalization runtime;
- native artifact hash binding and ELF/Mach-O/COFF inspection;
- atomic proof writer;
- authenticated DSSE/Sigstore envelope;
- English counterpart.

## Next phases

1. Lexer/Parser byte spans and immutable effective policy snapshot.
2. Ethical Checker evidence export.
3. LLVM/object binding, format inspection and atomic output.
4. CLI integration.
5. Standard authenticated envelope and English parity.

Phase 2 is a library verifier, not a production-ready deployment verifier.
