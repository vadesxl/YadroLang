# Flow-gap analysis for YadroLang

## Summary

The current compiler security model is structurally sound but semantically incomplete. The active flow analysis in `src/этика_v21.py` and `src/этика_поток.py` tracks labels on values, but it does not consistently combine label information with the active control context (`pc_метки`) when values are assigned, returned, or emitted. This leaves multiple unblocked implicit-flow paths even though LLVM verification succeeds.

## Confirmed root causes

### 1) Direct output bypass: `печать` is not treated as a sink

`src/main.py` compiles the program and emits a native object, but the ethical layer only checks calls whose names appear in `СТОКИ`. In `src/этика_v21.py`, `СТОКИ` includes network and filesystem APIs but omits `печать`. The sink check in `_сканировать_выражение` therefore blocks `сеть.отправить(...)` and similar calls, but says nothing when the program prints a secret through `печать(...)`.

This directly explains the reproduced case:

```
если среда.секрет() {
    печать(1)
}
```

The runtime output path is still reachable even though the compiler accepts the program.

### 2) Entry-point return value bypass

The compiler driver in `src/main.py` generates a `main` wrapper that calls `старт()` and prints its result. That return value is emitted outside the ethical analysis that checks sink calls inside function bodies. There is no explicit “final program output” security check that says: if `старт()` returns a tainted value, it must be rejected before native emission.

This explains the reproduced case:

```
функ старт() требует [ДоступСети] {
    вернуть среда.секрет()
}
```

The return value is treated as ordinary numeric output rather than a final sink of sensitive data.

### 3) Control labels are not propagated into assignments and returns

The current logic in `_метки(...)` and `_метки_возврата(...)` computes data labels from values and environment variables, but it does not incorporate the active control state when values are assigned or returned under a tainted condition.

Example:

```
пусть x = 0
если среда.секрет() {
    x = 1
}
вернуть сеть.отправить(x)
```

The variable `x` is assigned a constant, and the data-label analysis sees a clean literal. It never merges in the condition-derived `pc_метки`, so the assignment is incorrectly considered clean.

### 4) The loop fixpoint does not include condition-derived taint as the loop stabilizes

In `_фикспойнт_цикла(...)`, the loop state is merged from the body environment and the outer environment, but the active condition label is not treated as part of the stable state with the same update discipline as if/else branches. This allows a loop condition to become sensitive during iteration without the sensitive label being reflected in subsequent body analysis.

### 5) Branch merging reintroduces stale labels

The merge logic in `_сканировать_тело(...)` and `_метки_возврата(...)` is essentially:

```
окружение = self._объединить(окружение, левое, правое)
```

This joins the old environment and both branch states. If both branches sanitize the value in the same way, the stale pre-branch variable labels can still leak back into the merged environment. That creates the false positive in the branch-sanitizer case and is a sign that the merge rule is not preserving post-branch sanitization correctly.

## Proposed fix direction

### A) Treat all user-visible outputs as sinks

Add `печать` and final entry/output paths to the security sink model, and enforce the same taint rule for them as for other sinks. The compiler should reject any tainted value before it becomes program output.

### B) Make `pc_метки` part of the value-transfer function

The transfer function should be conceptually:

```
labels(value, env, pc) = data_labels(value, env) ∪ pc
```

for assignments, returns, and function-call effects that occur under a tainted condition. That must apply to:

- assignments inside `если`
- returns inside `если`
- helper effects reached from a tainted conditional caller
- loop-body and loop-condition updates

### C) Fix loop fixpoint semantics

Loop conditions should participate in the fixpoint as an explicit taint source. The analysis should evaluate the loop condition under the current environment, add those labels to the loop `pc`, and then recalculate body effects until convergence.

### D) Preserve post-branch sanitized state

When both branches sanitize the same value, the merge should keep the sanitized post-state instead of reintroducing the old pre-state. This requires a different join operation for branch states than a raw set union of all labels.

## Implementation priority

1. `печать` sink + final return output check
2. assignment propagation from `pc`
3. return propagation from `pc`
4. caller `pc` into callee summary effects
5. loop fixpoint including condition taint
6. branch-merge sanitizer fix
7. final regression pass on all 8 test cases

## Acceptance criteria

The branch is ready to consider the security issue closed only when all eight tests under `tests/ethics_gaps/` pass and the compiler rejects the reproduced leaks without weakening the allowlist of valid security policies.

## Status

This is the working conclusion from the current review: the project has a real compiler pipeline and a meaningful interprocedural flow analysis, but the current transfer rules are incomplete for control-driven leaks and output sinks.
