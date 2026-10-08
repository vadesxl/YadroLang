# Patch queue for `agent/compiler-fix`

## Phase 1: output sinks and final return output
- Add `печать` to the sink table.
- Check `старт()` return value as final program output.
- Reject anything leaving the program via return while the return labels are non-empty.

## Phase 2: assignment and return propagation
- Merge `pc_метки` into assignment transfer.
- Merge `pc_метки` into return transfer.
- Ensure conditional assignments keep their implicit dependence.

## Phase 3: call summaries and helper effects
- Add `pc`-aware summary entries for helper calls.
- Propagate caller control context into callee output summaries.
- Re-check nested helper taint chains.

## Phase 4: loop fixpoint and branch merge
- Fold `condition_labels` into loop `pc` state.
- Correct stale label merge after sanitization in both branches.

## Phase 5: validation
- Re-run `tests/ethics_gaps/`
- Verify the full suite is green and that the false positive is fixed.
