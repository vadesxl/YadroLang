# Печать Ядра: implementation map

Статус: план после принятия [нормативного дизайна](PROOF_SEAL.md). Команды не реализованы.

## Existing inventory

- `src/этика_v21.py`: bounded summaries, PC labels, sanitizer audit and mandates; current audit record is insufficient as proof schema.
- `src/guard_impl.py`: invocation policy, JSON/SARIF and exit classes; mutable runtime policy must be replaced by immutable snapshot for evidence.
- `src/mcp_guard_v2.py`: bounded deterministic graph, roots and fixpoint updates.
- `src/кодоген_verified.py`: verified LLVM and stable ABI symbols.
- `src/main.py`: native emission; proof finalization belongs after successful object write.

## Phase 1 internal types

Future module uses frozen values:

```text
EffectivePolicySnapshot
AnalysisEvidence
CallSiteEvidence
ExternalAssumption
FixpointEvidence
SubjectBinding
ProofSealCore
```

Fields use tuples. Constructors validate NFC, byte lengths, uniqueness and canonical ordering. Serializer accepts these types only, never arbitrary dicts or audit strings.

## Version dispatch

Strict verifier begins with bounded duplicate-rejecting JSON preflight that extracts only schema/policy/LLVM version tuple. It then dispatches exact strict validator. Do not validate unknown versions with v1 schema, and do not canonicalize policy/LLVM before support decision.

## Ethical Checker work

Future changes retain caller context, bounded reachability from entries, before/after label states, mandate evidence, fixpoint metadata and assumptions. Return immutable evidence only after successful full check. Existing diagnostics stay authoritative.

## Policy snapshot

Build one immutable effective policy from built-ins plus invocation entries. Semantic arity, Ethical Checker and evidence consume the same snapshot. Hash its versioned canonical bytes. Never serialize resettable module globals.

## Source spans

AST currently mostly stores lines. Stable IDs require UTF-8 byte start/end spans from lexer/parser. This is prerequisite work. Until then, implementation must not fake stable IDs from line numbers.

## Canonical serializer

Implement explicitly, not via default `json.dumps` assumptions:

- type-directed values;
- exact string escaping golden vectors;
- NFC rejection;
- key and array ordering;
- integer-only numbers;
- payload self-digest exclusion;
- domain-separated golden vectors for module, call-site and assumption IDs.

## LLVM/native binding

Normalizer parses/verifies and serializes through pinned compatibility. Coordinator emits object, inspects exact format/machine, hashes bytes, finalizes seal and atomically replaces output in trusted parent directory. Proof is absent on failure.

Avoid generic callbacks between emission and hashing.

## Verifier components

- bounded byte reader and nesting-aware duplicate-key parser;
- minimal version preflight;
- strict structural and semantic validator independent of optional schema library;
- NFC, ordering, span and safe-path validator;
- canonical serializer and digest comparison;
- ELF/Mach-O/COFF bounded header inspector;
- deterministic renderer with explicit trust state.

No user-path imports, subprocess, network or artifact execution.

## Test modules

- `test_proof_canonical.py`: exact bytes, NFC, all ordering, self-digest and ID vectors.
- `test_proof_preflight.py`: duplicate keys, bounds, unknown version tuple and dispatch order.
- `test_proof_parser_adversarial.py`: depth, sizes, unknown fields, unsafe paths and spans.
- `test_proof_binding.py`: artifact/policy/target mutation and swaps.
- `test_proof_object.py`: malformed/truncated ELF, Mach-O and COFF plus architecture mismatch.
- `test_proof_evidence.py`: direct, sanitized, implicit, recursive and assumptions.
- `test_proof_native.py`: cross-platform object verification without skip.
- `test_proof_cli.py`: exit classes, inspect wording, JSON trust state and UTF-8 subprocesses.

## Benchmarks

Measure compile without/with proof, serialization, verification, payload bytes and call-site count. No threshold before repeated baseline.
