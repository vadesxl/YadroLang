# Separate AST validator PR plan

Status: design plan only. Do not implement inside checked-arithmetic PR #41.

## Problem

Parser-produced syntax trees have parser nesting bounds, but library callers can directly construct dataclass AST objects. Existing semantic collection, type checking, Ethical Checker and CodeGen recursively traverse those objects independently. Deep trees, cycles, shared aliases, malformed child types and forged metadata can therefore cause raw recursion/resource failures, inconsistent acceptance or repeated work.

## Proposed scope

Create one pre-semantic structural validator called at every public AST-consuming compiler boundary before mutation or analysis. Keep it independent of arithmetic policy and LLVM lowering.

### Normative bounds

- Maximum graph depth: versioned constant, initially no greater than the parser's supported nesting contract.
- Maximum distinct nodes and maximum total edges: explicit finite constants with benchmark evidence.
- Maximum functions, statements per block, parameters, call arguments and identifier/string metadata lengths.
- Source line must be an exact non-negative bounded integer, never bool.

### Identity and graph rules

- Iterative traversal, not Python recursion.
- Three-color identity tracking for deterministic cycle detection.
- Visit each object identity once to bound shared-subtree work.
- Define alias policy explicitly: immutable expression sharing may be accepted only if downstream passes do not mutate nodes; otherwise reject all multi-parent nodes fail-closed.
- Reject custom subclasses unless a versioned extension registry explicitly permits them.
- Reject unexpected attributes where dataclass layout is part of the trusted schema.

### Shape validation

Validate exact node classes and child schemas for every AST type:

- `Программа.функции`, `Функция.параметры/тело/мандаты` are bounded lists of expected values.
- `Бинарный.оп` is one of the supported operators and both children are expression nodes.
- Calls have a normalized identifier and bounded expression arguments.
- Statements contain exact child types; missing children fail closed.
- Numeric literal payload is exact signed-i64 int, excluding bool.
- Bool/string/name payloads have exact types and scalar/length constraints.
- Inferred-type attributes are not trusted input; validator clears or rejects forged analysis metadata before type checking.

### Diagnostics

Use stable source-error codes without object repr or payload reflection:

- cycle;
- depth bound;
- node/edge/count bound;
- wrong child type;
- unsupported subclass/field;
- malformed metadata.

Messages include only stable node kind, reason code and bounded source line. No raw `repr`, custom `__str__`, identifiers or string contents.

## Public boundaries

Wire the validator before:

1. semantic collectors and call/entry validation;
2. type inference and return-path analysis;
3. Ethical Checker;
4. CodeGen facade and verified backend;
5. future Proof Seal evidence export;
6. any serializer/deserializer accepting AST-like input.

No downstream pass may assume parser provenance.

## Adversarial acceptance suite

- self-cycle and two-node cycle;
- deep linear tree just below/at/above limit;
- wide node/edge exhaustion;
- shared subtree and diamond graph;
- missing left/right child;
- wrong list/scalar collection type;
- custom node subclass and object with hostile `__repr__`/`__str__`;
- bool/float/string/None/custom numeric payload;
- out-of-i64 literal;
- forged inferred types and unexpected fields;
- malformed source lines including bool, negative and huge integers;
- parser-produced corpus remains accepted;
- bounded runtime and memory benchmark;
- Linux, macOS and Windows mandatory CI without skip.

## Delivery phases

1. Normative validator contract and threat-model update.
2. Iterative identity-aware validator plus focused adversarial tests.
3. Integration at all public boundaries and removal of duplicated unsafe walkers where practical.
4. Differential parser-produced versus direct-AST behavior tests.
5. Independent exact-head review before merge.

This work needs a separate branch and PR after explicit Vadym approval.
