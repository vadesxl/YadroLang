# Call-site identity correction before v1 freeze

Status: normative supplement to `PROOF_SEAL.md`. The earlier draft omitted inputs required for offline recomputation and is intentionally not compatible.

A serialized call site contains `id`, `module_id`, `semantic_kind`, `caller`, `callee`, `span`, all semantic evidence sets and `status`. `compiler.frontend` is taken from the top-level compiler identity and is not duplicated. V1 permits exactly one stable, non-localized semantic kind: `call`.

The normative content ID is:

```text
SHA-256("YADRO-CALL-SITE\0" || frontend || "\0" || module_id || "\0" || caller || "\0" || callee || "\0" || semantic_kind || "\0" || start_byte || "\0" || end_byte || "\0" || ordinal)
```

The domain separator already ends in NUL; every following identity field is separated by exactly one NUL, matching the shared Phase 1 implementation and golden vector. `module_id` is lowercase SHA-256. Integers are decimal values in `0..9007199254740991`. Identity strings are NFC Unicode scalar sequences; surrogate code points are forbidden. The verifier recomputes this formula through the shared Phase 1 implementation and compares it in constant time.

Identity is not completeness. Verification proves consistency of recorded call sites, not that a producer recorded every semantic call. Compiler integration and coverage invariants are future work. An unsigned seal proves consistency, not authenticity or provenance; `inspect` is not a security gate. No whole-program formal-proof or production-readiness claim is made.
