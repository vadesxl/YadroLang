# Печать Ядра: implementation status

## Phase 1 implemented in stacked PR

- frozen, slotted typed evidence model;
- canonical factories with duplicate rejection and UTF-8 ordering;
- NFC/type/hash/bounds/path/span validation;
- deterministic UTF-8 JSON serialization with one trailing LF;
- domain-separated module and call-site IDs;
- content-addressed assumption IDs;
- unsigned seal self-digest excluding the digest field;
- model, canonicalization, ID, adversarial and permutation tests;
- independent `proof_seal_serialize` benchmark metric.

Phase 1 exposes a library model only. It does not accept untrusted proof files and provides no authenticity.

## Existing integration inventory

- `src/этика_v21.py`: bounded summaries, PC labels, sanitizer audit and mandates. Current audit records are not proof evidence.
- `src/guard_impl.py`: invocation policy and diagnostics. Mutable runtime policy must become one immutable effective snapshot before evidence integration.
- `src/mcp_guard_v2.py`: bounded deterministic graph and fixpoint metadata, not yet exported as seal evidence.
- `src/кодоген_verified.py`: verified LLVM and ABI symbols, not yet normalized or bound.
- `src/main.py`: native emission, not yet coordinated with proof output.

## Not implemented

- bounded untrusted JSON parser and version preflight;
- structural/offline verifier or CLI commands;
- Ethical Checker or MCP evidence export;
- UTF-8 source spans from Lexer/Parser;
- LLVM normalization runtime;
- native artifact hash binding and object inspection;
- atomic proof writer;
- authenticated DSSE/Sigstore envelope;
- English counterpart.

## Next phases

1. Bounded duplicate-key parser, version preflight and strict verifier.
2. Lexer/Parser byte spans and immutable effective policy snapshot.
3. Ethical Checker evidence export.
4. LLVM/object binding, format inspection and atomic output.
5. Standard authenticated envelope and English parity.

Each phase remains a separate reviewed PR. Phase 1 is not production-ready and does not implement commands shown in `PROOF_SEAL.md`.
