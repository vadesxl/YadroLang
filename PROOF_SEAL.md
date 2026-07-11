# Печать Ядра v1

Статус: нормативный дизайн, не реализованная команда и не release claim.

## Назначение

Печать Ядра (`Yadro Proof Seal`, расширение `.yproof`) является детерминированным compile-time evidence artifact. Она связывает успешный анализ policy с verified LLVM module и точными bytes emitted native object. Auditor может проверить object, policy и seal offline, без исходников и без исполнения object.

В исследованной выборке прямой продуктовый аналог не найден. Это не заявление об абсолютной уникальности или патентной чистоте.

Seal доказывает только поддерживаемый policy contract относительно явно перечисленных assumptions. Seal не доказывает, что AI этичен вообще, и не заменяет runtime security для динамических свойств.

## Trust modes

V1 core является unsigned. Его self-digest обнаруживает corruption и mismatch, но не дает authenticity: атакующий, способный согласованно заменить artifact, policy и seal, может пересчитать все hashes. Unsigned verification имеет смысл только с отдельным trusted delivery channel или digest, закрепленным trusted CI/release metadata.

Trust state является машиночитаемым top-level object: `{"mode":"unsigned","authenticity":"not-provided"}`. JSON verifier output обязан повторять эти два поля; text output обязан писать `unsigned: authenticity not established` и не использовать `trusted` для успешного unsigned result.

Защита от coordinated substitution требует future DSSE/Sigstore envelope или externally authenticated seal digest. Signature envelope не входит в v1 core.

## Pipeline

```text
source -> parse -> semantic/types -> Ethical Checker -> immutable evidence
                                                     |
                                                     v
                                  LLVM CodeGen -> parse/verify
                                                     |
                                                     v
                                    native object -> exact digest
                                                     |
                                                     v
                                  canonical seal -> atomic write
```

Valid-looking seal не создается при policy violation, LLVM verification failure или object emission failure. Final write uses temporary regular file in destination directory, flush, fsync where supported and atomic replace. Symlink and non-regular destinations are rejected before creation and checked before replace. Parent output directory is trusted and not writable by attackers.

## Deterministic core

Schema identifier: `yadro-proof-seal-1.0`.

Canonical bytes:

- UTF-8 without BOM;
- strings must already be Unicode NFC, non-NFC input is rejected;
- object keys sorted by Unicode code point;
- compact separators `,` and `:`;
- non-ASCII emitted directly, never `\u` escaped;
- quote, backslash and controls use lowercase JSON escapes; `/` is not escaped;
- one trailing LF;
- decimal integers without leading or negative zero;
- floating point values forbidden;
- duplicate keys and unknown fields rejected;
- no timestamps, hostnames, usernames or absolute paths.

All arrays have explicit order:

- semantic sets, including every labels, capabilities, sanitizers, declassified labels, policy rules, implicit labels and assumption-ID array, sort ascending by canonical UTF-8 bytes and contain no duplicates;
- `call_sites` sort ascending by call-site `id`;
- `assumptions` sort ascending by assumption `id`;
- `entry_points` and `reachable_entries` sort ascending by ABI symbol canonical UTF-8 bytes;
- fixpoint `lattice_labels` sorts ascending by canonical UTF-8 bytes.

Verifier rejects arrays that are unique but not in required order.

`seal_sha256` is excluded from its own payload. Remove top-level member, canonicalize remaining object and compute:

```text
SHA-256("YADRO-PROOF-SEAL\0" || "1.0\0" || canonical_payload_without_seal_sha256)
```

Verifier also rejects received bytes that are not canonical encoding of parsed full object. Self-digest does not authenticate payload.

## Bounds

V1 limits: 1 MiB seal, JSON depth 16, 10,000 call sites, 256 entry points, 2,000 assumptions, 32 labels/capabilities/sanitizers per call site, 256 UTF-8 bytes per identifier and 512 UTF-8 bytes per diagnostic module path. Bounds are checked before proportional nested allocations.

## Subject binding and version discovery

`subject` contains open version fields before their digests:

- `policy_schema_version`, currently `yadro-policy-1.0`;
- `llvm_normalization_version`, currently `yadro-llvm-normalization-1.0`;
- `source_sha256` over exact accepted source bytes;
- `policy_sha256` over canonical validated effective policy;
- `llvm_sha256` over normalized verified LLVM text;
- `artifact_sha256` over exact emitted object bytes;
- `target_triple` and `artifact_kind`.

Verifier first checks open version fields against supported implementations. Unsupported version fails before attempting policy or LLVM canonicalization. Version strings are also included in their domain-separated canonical inputs, preventing version/hash ambiguity.

Effective policy serialization includes policy schema version, complete sorted sources/sinks/sanitizers and built-in defaults selected by compiler version. Verifier cannot substitute current defaults.

LLVM normalization parses and verifies module, serializes through pinned compatibility, normalizes LF and appends one LF. Stability across LLVM versions is not promised, so `compiler.llvm_compatibility` remains mandatory.

Object digest is exact-byte binding. Cross-toolchain reproducibility is not promised. Without source or LLVM IR, verifier can recompute artifact/policy hashes but source/LLVM and analysis remain compiler attestations whose authenticity depends on trust mode.

## Stable call-site identity

Line number alone is not identity. ID hashes domain-separated canonical tuple:

```text
frontend\0module-id\0caller-abi\0callee-abi\0ast-kind\0normalized-span\0ordinal
```

`module-id` hashes exact source bytes plus frontend. Span identity uses UTF-8 byte offsets; module path is diagnostic only. Ordinal is preorder among effectful calls after parser normalization. Any source-byte change may invalidate all IDs by design. Duplicate IDs fail closed.

Diagnostic paths use `/`, are relative and contain no empty, `.` or `..` segment, controls, drive or UNC prefix. Semantic validation, not regex alone, is security boundary.

## Evidence model

Typed immutable evidence comes from Ethical Checker, never human audit text. Each reachable effectful call records identity/span, caller/callee ABI, reachable entries, required/declared capabilities, incoming/outgoing labels, sanitizers/declassification, policy rules, implicit labels, assumptions and status `allowed`.

Violation produces diagnostics and no seal. Partial reports cannot use `.yproof` schema or success status. Fixpoint metadata contains algorithm, sorted lattice labels, updates and bound, never timing.

## FFI and tool trust boundary

Each external assumption records stable ID, ABI symbol/signature, capability, taint transformation, trusted-sanitizer flag, ownership/lifetime, no-retain contract and optional implementation digest.

Компилятор доказал свойства программы относительно перечисленных assumptions, но не доказал соблюдение assumptions внешней реализацией.

Capability does not make code trusted. Sanitization does not extend lifetime or alter provenance. Missing assumption fails closed.

## MCP evidence

Only versioned Yadro MCP security manifest is supported. Evidence may bind canonical manifest/graph digests, roots, fixpoint count, labels, sanitizers, capabilities and per-tool evidence. This is not universal MCP certification.

## Offline verifier

Verifier performs no network, artifact execution or plugin loading. It enforces schema/bounds/NFC/order/paths/canonical bytes, recomputes self/policy/artifact digests and inspects object format and architecture:

- ELF: magic, class, endianness, `e_type == ET_REL` and `e_machine` matching target;
- Mach-O: 64-bit object magic, file type `MH_OBJECT` and `cputype/cpusubtype` matching target;
- COFF: complete header, Machine `0x8664` for AMD64, section table bounds and target match.

Filename extension and claimed `artifact_kind` are not trusted. Inspected format/machine must match schema, target triple and deployment expectation. Output is deterministic and includes machine-readable trust state.

Proposed, not implemented:

```bash
yadro-guard compile program.яд --policy policy.json --emit-proof program.yproof -o program.o
yadro-guard proof verify program.yproof --artifact program.o --policy policy.json
yadro-guard proof inspect program.yproof --format json
```

`inspect` never implies verification.

## Exit classes

- `0`: structure and supplied bindings match, trust mode reported separately;
- `2`: policy violation during compile;
- `3`: malformed/unsupported/mismatched proof input;
- `4`: internal failure.

## Threats and non-goals

With trusted channel or future authenticated envelope, seal detects artifact/policy/seal swap, stale bytes, target mismatch and downgrade. Parser also handles duplicate keys, Unicode confusion, unsafe paths, resource exhaustion, identity collisions, hidden assumptions and nondeterminism.

Unsigned core does not stop coordinated replacement. Other non-goals: untrusted output directory, malicious compiler/build host, compromised sanitizer/tool, hardware attacks, unsupported language properties, stolen future key, equal cross-toolchain object hashes and proof of general AI benevolence.

## Required implementation tests

- byte-identical output and golden JSON escapes;
- every array category rejects unsorted or duplicate values;
- machine-readable unsigned trust output;
- unsupported policy/LLVM versions fail before canonicalization;
- NFC, duplicate/unknown fields, truncation, size/depth and non-canonical bytes fail;
- paths/symlinks fail under trusted parent contract;
- artifact/policy/target swaps and byte mutation fail against fixed trust anchor;
- coordinated substitution accepted unsigned and rejected by future envelope;
- ELF `e_machine`, Mach-O `cputype/filetype`, COFF Machine/table bounds validated;
- call-site collision attempts fail;
- direct/sanitized/implicit/recursive flows and FFI assumptions match;
- violation emits no seal;
- Linux/macOS/Windows verification, no skip, hard missing-toolchain failure and finite timeouts.

## Benchmarks and phases

Measure compile without/with proof, serialization, verification and MCP evidence with median, p95, rounds, bytes and call-site count.

Phases: immutable evidence/canonical serializer; strict verifier; LLVM/object binding and atomic output; Ethical Checker/MCP export; standard authenticated envelope and English parity. Each phase is separate reviewed PR. This design PR implements no CLI command.
