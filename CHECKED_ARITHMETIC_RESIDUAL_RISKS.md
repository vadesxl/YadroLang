# Checked arithmetic residual-risk map

Status: exact-head engineering map for PR #41, not a production-readiness claim.

## Covered on the current branch

- Checked add/sub/mul use LLVM overflow intrinsics and trap.
- Checked division guards zero and `INT64_MIN / -1` before `sdiv`.
- O2 tests verify semantic guard/trap survival without relying on unstable intrinsic spelling.
- Unknown and abbreviated direct CLI flags fail closed.
- Unknown/non-string arithmetic profiles, including bool, fail closed.
- Constant-analysis depth exhaustion is distinct from non-constant input and fails closed as `ЯДРО-А1002`.
- Default constant division checks mirror signed i64 wraparound per arithmetic operation.
- Required native safe/trap paths run on Linux, macOS and Windows without skip.
- Direct malformed numeric AST literals reject bool, float, string, None, custom objects and out-of-i64 integers before LLVM construction.

## Open compiler risks

1. **Recursive structural walkers**: `_собрать`, type checking, Ethical Checker and CodeGen still recurse over direct-construction ASTs without one shared structural node/count/depth validator. Parser-produced trees are bounded, but library callers can construct deeper graphs, cycles or aliased structures. Required follow-up: bounded identity-aware AST validation before every public compiler boundary.
2. **Cycles and aliasing**: direct AST cycles can cause recursion/resource exhaustion; repeated shared nodes can amplify work and make diagnostics order-dependent. No whole-AST cycle/alias contract exists yet.
3. **Default arithmetic remains unchecked**: add/sub/mul intentionally wrap. The compiler only folds default expressions as needed to detect dangerous division. Users must explicitly select checked arithmetic.
4. **Constant evaluator duplication**: Python evaluation and LLVM lowering remain separate implementations. Differential property tests over generated expression trees are not yet exhaustive.
5. **Comparisons and conditions**: wraparound-aware constant semantics are not used to simplify or prove comparisons/conditions. No optimization claim is made, but future constant folding must preserve i64 semantics.
6. **Diagnostic payload boundaries**: arithmetic diagnostics use stable messages and source lines, but native toolchain failures may include boundedness-unchecked stderr from external tools. Secret-safe redaction and size caps remain future hardening.
7. **CLI path exposure**: machine-readable diagnostics include an absolute resolved source path. This is intentional current behavior but can expose local layout in shared reports; a privacy mode is not implemented.
8. **Argparse process boundary**: parser errors write usage text and raise `SystemExit` before `run()` classification when the library entry is called with malformed argv. Existing subprocess behavior is controlled, but a fully library-safe structured parse-error contract is not implemented.
9. **Optimization matrix**: O2 is covered with the pinned llvmlite/LLVM version. Cross-version LLVM canonicalization and future pass pipelines require renewed exact-head tests.
10. **Trap environment**: the contract guarantees abnormal termination, not a stable signal/exit code or recoverability. Trap handling under sanitizers, embedded runtimes and unusual hosts is not fully characterized.

## Open project risks outside arithmetic

- Current pointer-only `%s` strings are not memory-safe; PR #40 is design-only.
- Proof Seal is unsigned consistency evidence, not authenticity, provenance or completeness.
- Proof Seal is not yet fully bound to compiler source spans, policy snapshot, normalized LLVM and exact native object bytes.
- English frontend does not have Proof Seal and full RU/EN differential parity is not established.
- Runtime Guard is design-only; no runtime mediation, quarantine or authenticated recovery implementation exists.
- Legacy shell-negative workflow checks accept any nonzero exit and have stale `v2.0` labels; reason-specific unittest lanes are stronger, but cleanup remains.
- Actions/toolchains and runner images evolve; green CI is exact-head evidence, not a permanent platform guarantee.

## Review rule

Every new commit invalidates prior CI and approval. New bypass classes must add a neighboring mutation family, full cross-platform CI, an updated residual-risk entry and a fresh independent exact-head review.
