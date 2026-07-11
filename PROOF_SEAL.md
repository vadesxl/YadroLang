# Печать Ядра v1

Статус: нормативный дизайн, не реализованная команда и не release claim.

## Назначение

Печать Ядра (`Yadro Proof Seal`, расширение `.yproof`) является детерминированным compile-time evidence artifact. Она связывает успешный анализ policy с verified LLVM module и точными bytes emitted native object. Auditor может проверить object, policy и seal offline, без исходников и без исполнения object.

В исследованной выборке прямой продуктовый аналог не найден. Это не заявление об абсолютной уникальности или патентной чистоте.

Seal доказывает только поддерживаемый policy contract относительно явно перечисленных assumptions. Seal не доказывает, что AI этичен вообще, и не заменяет runtime security для динамических свойств.

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

Valid-looking seal не создается при policy violation, LLVM verification failure или object emission failure. Final write использует temporary file в destination directory, flush, fsync where supported и atomic replace. Failure до replace удаляет temporary file. Symlink destinations and non-regular existing targets are rejected before creation and checked again immediately before replace.

## Deterministic core

Schema identifier: `yadro-proof-seal-1.0`.

Canonical bytes:

- UTF-8 without BOM;
- evidence strings must already be Unicode NFC, non-NFC input is rejected rather than silently rewritten;
- JSON object keys sorted by Unicode code point;
- compact separators `,` and `:`;
- one trailing LF;
- integers encoded in decimal without leading zero;
- booleans and null use JSON spelling;
- floating point values, NaN and Infinity are forbidden;
- duplicate keys and unknown fields are rejected;
- arrays use semantic stable ordering defined by each field;
- timestamps, hostnames, usernames and absolute paths are forbidden in deterministic core.

`seal_sha256` is not part of its own payload. To compute it, remove the top-level `seal_sha256` member, canonicalize the remaining object, then compute:

```text
SHA-256("YADRO-PROOF-SEAL\0" || "1.0\0" || canonical_payload_without_seal_sha256)
```

Verifier rejects a document whose received bytes are not the canonical encoding of the parsed object, in addition to checking the digest. This prevents alternate encodings from sharing one logical payload.

A SHA-256 digest is not a digital signature. An optional future signature envelope must use a reviewed standard such as DSSE/Sigstore and remain outside deterministic core.

## Bounds

Verifier limits for v1:

- seal file: 1 MiB;
- JSON nesting: 16;
- call sites: 10,000;
- entry points: 256;
- assumptions: 2,000;
- labels per call site: 32;
- capabilities per call site: 32;
- sanitizers per call site: 32;
- identifier: 256 UTF-8 bytes;
- source span path: module-relative normalized path, 512 UTF-8 bytes.

Bounds are checked before allocating proportional nested structures. Malformed, oversized or unsupported input fails closed as source/proof error, not internal failure.

## Subject binding

`subject` contains:

- `source_sha256`: exact source file bytes accepted by the compiler, before parsing; BOM and invalid UTF-8 are rejected;
- `policy_sha256`: canonical validated effective policy, including built-in and invocation-local entries, not raw formatting;
- `llvm_sha256`: verified LLVM text normalized by versioned `yadro-llvm-normalization-1.0`;
- `artifact_sha256`: exact emitted object bytes;
- `target_triple`: actual emission target;
- `artifact_kind`: for example `elf-object`, `macho-object`, `coff-object`.

`yadro-llvm-normalization-1.0` parses and verifies the module, emits canonical LLVM text through the pinned llvmlite/LLVM toolchain, normalizes LF line endings and appends one LF. Compiler and LLVM versions remain part of evidence because textual stability across LLVM versions is not promised.

Object digest is exact-byte binding. Reproducibility across different LLVM/clang versions, hosts or targets is not promised. LLVM digest supports comparison only within the same documented normalization and LLVM compatibility versions.

## Stable call-site identity

Line number alone is not identity. Canonical tuple:

```text
frontend\0module-id\0caller-abi\0callee-abi\0ast-kind\0normalized-span\0ordinal
```

Call-site ID:

```text
SHA-256("YADRO-CALL-SITE\0" || canonical_tuple)
```

`module-id` is SHA-256 of exact accepted source bytes plus frontend identity, never an absolute path. `normalized-span` contains UTF-8 byte offsets only; module path is diagnostic and is not part of identity. `ordinal` is preorder ordinal among effectful calls in caller after parser normalization. Caller/callee readable names are diagnostic only, ABI symbols and hash bind identity.

Any source-byte change may change module and call-site IDs. This conservative rule is intentional for artifact evidence. Duplicate call-site IDs are an internal compiler error during emission and invalid proof during verification.

Diagnostic module paths must use `/`, be relative, contain no empty, `.` or `..` segment, no NUL/control character and no drive/UNC prefix. Verifier performs semantic segment validation after schema validation; regex alone is not the security boundary.

## Evidence model

Typed immutable evidence is produced by Ethical Checker, never parsed from human-readable audit text.

For each reachable effectful call:

- call-site ID and normalized source span;
- caller and callee ABI symbols;
- reachable entry points;
- required and declared capabilities;
- incoming and outgoing labels;
- applied sanitizers and declassified labels;
- policy rule IDs;
- implicit control-flow labels;
- external assumption references;
- status `allowed`.

A successful seal contains no blocked call. Violations produce normal diagnostics and no seal. A partial analysis report may exist separately but cannot use `.yproof` schema or success status.

All sets are serialized as sorted unique arrays. Call sites sort by ID, assumptions by ID, entry points by ABI symbol. Bounded fixpoint metadata includes algorithm version, lattice labels, update count and configured bound, but not nondeterministic timing.

## FFI and tool trust boundary

For each external symbol, an assumption states:

- stable assumption ID;
- external ABI symbol and signature;
- required capability;
- taint transformation contract;
- whether compiler treats it as trusted sanitizer;
- ownership/lifetime contract;
- no-retain contract for borrowed views;
- implementation digest if supplied by trusted build input, otherwise `null`.

Компилятор доказал свойства программы относительно перечисленных assumptions, но не доказал соблюдение assumptions внешней реализацией.

Capability does not make external code trusted. Sanitization does not extend lifetime or alter provenance. Missing required assumption fails closed.

## MCP evidence

Only versioned Yadro MCP security manifest is supported. Seal may bind canonical manifest digest, tool graph digest, roots, fixpoint update count, labels, sanitizer nodes, privileged capabilities and per-tool evidence. This is not universal MCP certification.

## Offline verifier

Verifier:

- performs no network access;
- never executes artifact;
- loads no plugins;
- rejects duplicate keys, unknown fields, non-NFC strings and unsupported versions;
- enforces all bounds and safe relative-path segments;
- requires canonical received bytes;
- canonicalizes payload without `seal_sha256` and recomputes seal digest;
- recomputes effective-policy and exact artifact digests;
- checks target triple and artifact kind supplied by deployment context;
- uses constant-time digest comparison where practical;
- emits deterministic text or JSON and controlled exit codes.

Proposed commands, not implemented by this design PR:

```bash
yadro-guard compile program.яд --policy policy.json --emit-proof program.yproof -o program.o
yadro-guard proof verify program.yproof --artifact program.o --policy policy.json
yadro-guard proof inspect program.yproof --format json
```

`proof verify` does not need source. `inspect` never implies verification.

## Exit classes

- `0`: verified;
- `2`: policy violation during compile;
- `3`: malformed proof/input, unsupported schema, digest/target mismatch;
- `4`: internal failure.

Numeric values preserve existing CLI classes; implementation must add stable diagnostic codes for each verifier failure.

## Threats covered

- artifact, policy or seal swapping;
- stale seal after one-byte mutation;
- target mismatch and schema downgrade;
- duplicate-key and Unicode normalization confusion;
- unsafe diagnostic paths and symlink output replacement;
- unstable or colliding call-site identity;
- oversized/deep proof resource exhaustion;
- hidden FFI assumptions;
- nondeterministic evidence ordering.

## Explicit non-goals

- malicious compiler or compromised build host;
- compromised trusted sanitizer/tool implementation;
- hardware and microarchitectural attacks;
- properties outside supported language/policy subset;
- protection of a stolen future signing key;
- equal object hashes across toolchains;
- proof of general AI benevolence.

## Required implementation tests

- identical inputs produce byte-identical canonical proof;
- Unicode identifiers normalize consistently and non-NFC evidence is rejected;
- duplicate/unknown fields, unsupported version, truncation, excessive size/depth fail closed;
- non-canonical JSON bytes fail even when logical object matches;
- unsafe path segments, symlink destinations and target replacement races fail closed;
- artifact, policy, target and certificate swaps fail;
- one-byte artifact mutation fails;
- call-site collision attempts fail;
- sanitized, implicit and recursive flows produce expected evidence;
- FFI assumptions are explicit;
- policy violation produces no seal;
- Linux ELF, macOS Mach-O and Windows AMD64 COFF objects verify on their platform;
- wrong-platform object fails;
- no skip, missing toolchain hard-fails and subprocesses have finite timeout.

## Benchmarks

Measure separately compile without proof, compile with proof, canonical serialization, offline verification and MCP evidence generation. Report median, p95, rounds, payload bytes and call-site count. No hard threshold before an accumulated baseline.

## Implementation phases

1. Immutable `AnalysisEvidence`, `CallSiteEvidence`, `Assumption` and canonical serializer.
2. Strict bounded parser and offline verifier.
3. LLVM normalization, exact object binding and atomic output.
4. Ethical Checker and Yadro MCP evidence export.
5. Optional standard signature envelope and English counterpart parity.

Each phase is a separate reviewed PR. This design PR implements none of the proposed CLI commands.
