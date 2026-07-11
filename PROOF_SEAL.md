# Печать Ядра v1

Статус: нормативный дизайн, не реализованная команда и не release claim.

## Назначение

Печать Ядра (`Yadro Proof Seal`, `.yproof`) является детерминированным compile-time evidence artifact. Она связывает успешный policy analysis с verified LLVM module и точными bytes emitted native object. Auditor может проверить object, policy и seal offline, без исходников и исполнения object.

В исследованной выборке прямой продуктовый аналог не найден. Это не заявление об абсолютной уникальности или патентной чистоте. Seal доказывает только versioned policy contract относительно перечисленных assumptions, не общую этичность AI.

## Trust modes

V1 core unsigned. Self-digest обнаруживает corruption/mismatch, но не authenticity: coordinated replacement artifact + policy + seal остается возможным. Unsigned verification требует trusted delivery channel или externally anchored digest.

Машиночитаемый top-level trust state: `{"mode":"unsigned","authenticity":"not-provided"}`. JSON verifier output повторяет поля; text output пишет `unsigned: authenticity not established` и не использует `trusted` для unsigned success. Authenticated mode требует future DSSE/Sigstore envelope, не самодельную криптографию.

## Pipeline

```text
source -> parse -> semantics/types -> Ethical Checker -> immutable evidence
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

Seal отсутствует при policy violation, LLVM failure или object emission failure. Output uses temporary regular file in trusted destination directory, flush/fsync where supported and atomic replace. Symlink/non-regular destinations fail before creation and before replace. Untrusted parent directory is a non-goal.

## Two-stage verifier dispatch

Version discovery is a bounded preflight, not validation with the v1 schema:

1. read at most 1 MiB;
2. parse JSON with duplicate-key rejection and maximum nesting 16;
3. require top-level object and read only `schema`, `subject.policy_schema_version` and `subject.llvm_normalization_version` as bounded strings;
4. select an exact supported schema/canonicalizer tuple;
5. if unsupported, return controlled unsupported-version diagnostic without policy/LLVM canonicalization;
6. revalidate the already parsed value against selected strict schema, including unknown-field rejection.

Preflight does not accept the proof as valid and does not hash it. This avoids the chicken-and-egg failure where a v1 schema `const` would reject a future version before dispatcher can identify it.

## Deterministic core

Schema: `yadro-proof-seal-1.0`.

Canonical bytes:

- UTF-8 without BOM; strings must already be NFC;
- object keys sorted by Unicode code point;
- compact separators;
- non-ASCII emitted directly;
- standard lowercase JSON escapes for quote/backslash/controls, `/` unescaped;
- exactly one trailing LF;
- decimal integers without leading/negative zero; floats forbidden;
- every integer is in `0..9007199254740991` (`2^53-1`, JavaScript `Number.MAX_SAFE_INTEGER`);
- duplicate/unknown fields rejected;
- no timestamps, hostnames, usernames or absolute paths.

The safe-integer ceiling is normative for public cross-language JSON interoperability. It applies to source byte offsets, ordinals, fixpoint updates and bounds. Values above it, negative integers, booleans in integer positions, floats and exponent notation are rejected without rounding.

Array order:

- all semantic sets (labels, capabilities, sanitizers, declassified labels, rules, implicit labels, assumption IDs, lattice labels) sort by canonical UTF-8 bytes;
- `call_sites` sort by `id`;
- `assumptions` sort by `id`;
- `entry_points` and `reachable_entries` sort by ABI symbol canonical UTF-8 bytes.

All arrays are unique; unsorted unique arrays are rejected.

`seal_sha256` is excluded from payload:

```text
SHA-256("YADRO-PROOF-SEAL\0" || "1.0\0" || canonical_payload_without_seal_sha256)
```

Received full document bytes must also equal canonical encoding. Self-digest is not authentication.

## Bounds

V1: 1 MiB seal, depth 16, 10,000 call sites, 256 entries, 2,000 assumptions, 32 values per semantic set, 256 UTF-8 bytes per identifier, 512 per diagnostic module path and `MAX_SAFE_INTEGER = 9007199254740991` for every integer. Bounds are enforced before proportional allocation.

## Subject binding and versions

Open fields precede digests:

- `policy_schema_version = yadro-policy-1.0`;
- `llvm_normalization_version = yadro-llvm-normalization-1.0`;
- exact source, canonical effective policy, normalized verified LLVM and exact artifact SHA-256;
- target triple and artifact kind.

Version strings are included in domain-separated canonical inputs. Effective policy includes schema version, all sorted sources/sinks/sanitizers and selected built-ins. Verifier never substitutes current defaults.

LLVM normalization parses/verifies, serializes through pinned compatibility, normalizes LF and appends one LF. Cross-LLVM stability is not promised. Exact object binding is not cross-toolchain reproducibility.

Without source/IR, verifier independently recomputes policy/artifact hashes only; source/LLVM/analysis are compiler attestations whose authenticity depends on trust mode.

## Stable evidence identities

Module ID:

```text
SHA-256("YADRO-MODULE\0" || frontend || "\0" || exact_source_bytes)
```

Call-site ID:

```text
SHA-256("YADRO-CALL-SITE\0" || frontend || "\0" || module_id || "\0" || caller_abi || "\0" || callee_abi || "\0" || ast_kind || "\0" || start_byte || ":" || end_byte || "\0" || ordinal)
```

Assumption ID:

```text
SHA-256("YADRO-ASSUMPTION\0" || canonical_assumption_without_id)
```

Policy rule IDs are versioned identifiers from effective policy schema, not display text. Any source-byte change may invalidate every call-site ID by design. Duplicate IDs fail closed.

Span invariants are semantic checks beyond JSON Schema: `start_byte <= end_byte <= source_byte_length`; offsets lie on UTF-8 code-point boundaries; ordinal is unique within caller; span maps to the expected effectful AST node and callee. Since source-free verifier cannot independently re-map spans, these remain compiler attestations.

Diagnostic module path is not identity. It uses `/`, is relative and has no empty, `.`/`..`, control, drive or UNC segments. Semantic validation, not regex alone, is security boundary.

## Evidence model

Typed immutable evidence comes from Ethical Checker, never human audit text. Each reachable effectful call records identity/span, caller/callee ABI, reachable entries, required/declared capabilities, incoming/outgoing labels, sanitizers/declassification, policy rules, implicit labels, assumptions and `allowed` status.

Violation produces diagnostics and no seal. Partial report cannot use `.yproof`. Fixpoint evidence records algorithm, sorted lattice, updates and bound, not timing.

## FFI/tool trust boundary

Each external assumption records stable ID, ABI symbol/signature, capability, taint transformation, trusted-sanitizer flag, ownership/lifetime, no-retain and optional implementation digest.

Компилятор доказал свойства программы относительно перечисленных assumptions, но не доказал соблюдение assumptions внешней реализацией.

Capability does not confer trust. Sanitization does not extend lifetime or alter provenance. Missing assumption fails closed.

## MCP evidence

Only versioned Yadro MCP security manifest is supported. Evidence may bind canonical manifest/graph digests, roots, fixpoint count, labels, sanitizers, capabilities and per-tool evidence. This is not universal MCP certification.

## Offline verifier

No network, artifact execution or plugins. Verifier enforces schema/bounds/NFC/order/paths/canonical bytes, recomputes self/policy/artifact digests and inspects object:

- ELF: magic, class, endianness, header/section bounds, `ET_REL`, `e_machine`;
- Mach-O: 64-bit magic with correct endianness, load-command bounds, `MH_OBJECT`, `cputype/cpusubtype`;
- COFF: complete header, section table bounds, Machine (`0x8664` for AMD64).

Inspected format/machine must match artifact kind, target triple and deployment expectation. Filename is irrelevant. Deterministic output includes trust state.

Proposed only:

```bash
yadro-guard compile program.яд --policy policy.json --emit-proof program.yproof -o program.o
yadro-guard proof verify program.yproof --artifact program.o --policy policy.json
yadro-guard proof inspect program.yproof --format json
```

`inspect` never implies verification.

## Exit classes

`0` structural/binding match with trust state; `2` compile-time policy violation; `3` malformed/unsupported/mismatch; `4` internal failure.

## Threats and non-goals

With trusted channel/future envelope: detects swaps, stale bytes, target mismatch and downgrade. Parser handles duplicate keys, Unicode confusion, unsafe paths, resource exhaustion, ID collision, hidden assumptions and nondeterminism.

Unsigned coordinated replacement, malicious compiler/build host, compromised external implementation, untrusted output directory, hardware attacks, unsupported language properties, cross-toolchain reproducibility and general AI benevolence are non-goals.

## Required tests

- byte-identical output and golden JSON escapes;
- every array category rejects unsorted/duplicate values;
- machine-readable unsigned trust result;
- bounded preflight selects versions before strict schema and rejects unsupported tuple;
- NFC, duplicate/unknown fields, truncation, size/depth and non-canonical bytes fail;
- safe-integer boundaries accept `0`, `1`, `9007199254740990`, `9007199254740991` and reject larger, negative, boolean and floating values across schema/model/verifier;
- max integer serializes as exact decimal JSON without exponent notation or rounding;
- span/order/ID invariants and domain-separated golden vectors;
- paths/symlinks fail under trusted-parent contract;
- artifact/policy/target swaps and mutation fail against fixed trust anchor;
- coordinated substitution accepted unsigned and rejected by future envelope;
- strict ELF/Mach-O/COFF header, architecture and bounds checks;
- direct/sanitized/implicit/recursive flows and FFI assumptions;
- violation emits no seal;
- Linux/macOS/Windows, no skip, hard toolchain failure and finite timeouts.

## Phases

1. Immutable evidence and canonical serializer.
2. Bounded preflight, strict verifier and unsigned result.
3. LLVM/object binding and atomic output.
4. Ethical Checker/MCP export.
5. Standard envelope and English parity.

Each phase is a separate reviewed PR. This PR implements no command.
