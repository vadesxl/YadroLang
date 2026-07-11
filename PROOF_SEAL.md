# Печать Ядра v1

Статус: нормативный дизайн до public v1 freeze, не реализованная команда и не release claim.

## Назначение и границы

Печать Ядра (`Yadro Proof Seal`, `.yproof`) является детерминированным compile-time evidence artifact. Она связывает успешный policy analysis с verified LLVM module и точными bytes native object. Seal доказывает только versioned policy contract относительно перечисленных assumptions, не общую этичность AI, не completeness и не whole-program formal proof.

V1 core unsigned. Self-digest обнаруживает corruption/mismatch, но не authenticity или provenance. Машиночитаемый trust state: `{"mode":"unsigned","authenticity":"not-provided"}`. `inspect` не является security gate. DSSE/Sigstore является будущей отдельной фазой.

## Pipeline

```text
source -> parse -> semantics/types -> Ethical Checker -> immutable evidence
                                                       |
                                    LLVM CodeGen -> parse/verify
                                                       |
                                      native object -> exact digest
                                                       |
                                    canonical seal -> atomic write
```

Seal отсутствует при policy violation, LLVM failure или object emission failure.

## Two-stage verifier dispatch

Verifier bounded preflight:

1. читает не более 1 MiB;
2. разбирает JSON с duplicate-key rejection и depth 16;
3. извлекает только `schema`, `subject.policy_schema_version`, `subject.llvm_normalization_version` как bounded strings;
4. выбирает точный validator/canonicalizer tuple;
5. unsupported tuple даёт controlled version diagnostic;
6. затем выполняется полная strict validation с unknown-field rejection.

Preflight не принимает proof как valid и не хеширует его.

## Deterministic core

Schema: `yadro-proof-seal-1.0`.

Canonical bytes:

- UTF-8 без BOM, ровно один trailing LF;
- strings являются NFC Unicode scalar sequences, surrogate code points запрещены;
- object keys сортируются по Unicode code point;
- compact separators, non-ASCII emitted directly;
- integers только `0..9007199254740991`, floats запрещены;
- duplicate/unknown fields запрещены;
- semantic sets unique и сортируются по canonical UTF-8 bytes;
- `call_sites` и `assumptions` сортируются по `id`;
- никаких timestamps, hostnames, usernames или absolute paths.

`seal_sha256` исключается из payload:

```text
SHA-256("YADRO-PROOF-SEAL\0" || "1.0\0" || canonical_payload_without_seal_sha256)
```

Received document bytes должны совпасть с canonical encoding. Self-digest не является authentication.

## Bounds

V1: seal 1 MiB, depth 16, 10,000 call sites, 256 entries, 2,000 assumptions, 32 values per semantic set, 256 UTF-8 bytes per identifier, 512 UTF-8 bytes per diagnostic module path. Bounds проверяются до proportional allocation.

## Subject binding

Subject хранит visible `policy_schema_version = yadro-policy-1.0`, `llvm_normalization_version = yadro-llvm-normalization-1.0`, exact source/policy/normalized LLVM/artifact SHA-256, target triple и artifact kind. Verifier никогда не подставляет текущие defaults.

Без source/IR verifier независимо подтверждает только доступные bindings; source/LLVM/analysis остаются compiler attestations, authenticity которых зависит от trust mode.

## Stable evidence identities

Module ID:

```text
SHA-256("YADRO-MODULE\0" || frontend || "\0" || exact_source_bytes)
```

Serialized call site содержит `id`, `module_id`, `semantic_kind`, `caller`, `callee`, `span`, semantic evidence sets и `status`. `compiler.frontend` берётся из top-level compiler identity и не дублируется. V1 semantic-kind vocabulary содержит одно стабильное нелокализованное значение: `call`.

Call-site ID:

```text
SHA-256("YADRO-CALL-SITE\0" || frontend || "\0" || module_id || "\0" || caller || "\0" || callee || "\0" || semantic_kind || "\0" || start_byte || "\0" || end_byte || "\0" || ordinal)
```

Эта формула совпадает с shared Phase 1 implementation: domain separator уже содержит terminal NUL, затем identity fields соединяются одиночным NUL. `module_id` является lowercase SHA-256. `semantic_kind` обязан быть `call`. Verifier реконструирует inputs и сравнивает serialized/computed ID через constant-time comparison.

Assumption ID:

```text
SHA-256("YADRO-ASSUMPTION\0" || canonical_assumption_without_id)
```

Старый pre-freeze draft без `module_id`/`semantic_kind` был непроверяемым и намеренно не поддерживается. Это schema correction до public v1 freeze.

Span invariants: `start_byte <= end_byte`, offsets и ordinal находятся в safe-integer range. Mapping span к source node остаётся compiler attestation, пока source-free verifier не имеет source bytes.

Diagnostic module path не является identity, использует `/`, является relative и запрещает empty, `.`/`..`, controls, drive и UNC segments.

## Evidence model

Typed immutable evidence приходит из Ethical Checker. Каждый reachable effectful call записывает content-bound identity/span, caller/callee ABI, reachable entries, required/declared capabilities, incoming/outgoing labels, sanitizers/declassification, policy rules, implicit labels, assumptions и `allowed` status. Violation создаёт diagnostics и не создаёт seal.

External assumption хранит content ID, ABI symbol/signature, capability, taint transform, trusted-sanitizer flag, ownership/lifetime, no-retain и optional implementation digest. Компилятор доказывает свойства только относительно этих assumptions.

## Identity is not completeness

Verifier подтверждает identity только записанных call sites. Malicious или buggy producer всё ещё может опустить evidence. Completeness требует будущей compiler integration и coverage invariants. `verify_bytes` подтверждает consistency, не authenticity. Никакая часть v1 unsigned seal не заявляет production readiness или формальное доказательство общей этичности.

## Offline verifier

Verifier не использует сеть, plugins и не исполняет artifact. Он проверяет schema, bounds, NFC/scalars, ordering, paths, content IDs, canonical bytes, self/policy/artifact digests и bounded object headers. ELF/Mach-O/COFF format/machine должны соответствовать artifact kind и target triple. Filename не является доказательством.

## Exit classes

`0` structural/binding match с trust state; `2` compile-time policy violation; `3` malformed/unsupported/mismatch; `4` internal failure.

## Required tests

- byte-identical canonical output и golden domain vectors;
- every array rejects unsorted/duplicate values;
- version preflight before strict schema;
- NFC, surrogates, duplicate/unknown fields, truncation, size/depth и non-canonical bytes fail controlled;
- forged call-site ID с пересчитанным outer seal fail;
- mutation frontend/module/caller/callee/semantic_kind/span/ordinal обнаруживается;
- identity domain separation module/call-site/assumption;
- paths, references, artifact/policy/target swaps fail;
- Linux/macOS/Windows, no skip, hard failures и finite timeouts.

## Phases

1. Immutable evidence и canonical serializer.
2. Bounded preflight, strict verifier и unsigned result.
3. LLVM/object binding и atomic output.
4. Ethical Checker/MCP export и completeness invariants.
5. Standard authenticated envelope и English parity.

Каждая фаза проходит отдельное exact-head review. Этот документ не реализует команды.
