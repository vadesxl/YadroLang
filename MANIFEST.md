# YadroLang Compiler-Fix MANIFEST

## STATUS: Ready for GitHub Integration ✅

**Branch:** `compiler-fix-working`  
**Progress:** 3/6 patches done (50%)  
**Tests:** 3/3 passing  
**Quality:** ✅ Ready for helpers

## WHAT'S DONE

✅ Patch 1: печать as output sink  
✅ Patch 2: PC-propagation in assignments  
✅ Patch 3: PC-propagation in returns  
✅ Tests: test_patches_quick.py (3/3 passing)  
✅ Docs: 5 files created  

## WHAT'S TODO

⏳ Patch 4: Caller PC into callee summaries (HIGH complexity)  
⏳ Patch 5: Loop fixpoint with condition taint (MEDIUM)  
⏳ Patch 6: Branch-merge sanitizer fix (MEDIUM)  
⏳ Regression validation: 52 test cases  
⏳ Commercial MVP: CLI, policies, docs  

## KEY FILES

- `src/этика_v21_patched.py` - Main implementation (patches 1-3 applied)
- `test_patches_quick.py` - Validation tests (PASSING)
- `docs/analysis/flow-gaps.md` - Root cause analysis (from semantic phase)
- `SESSION_SUMMARY.md` - Quick reference
- `HOW_TO_GITHUB.md` - Helper integration guide

## QUICK COMMANDS

```bash
# Validate
python test_patches_quick.py

# Push to GitHub
git push origin compiler-fix-working

# Check commits
git log --oneline -5
```

## NEXT STEPS

1. Push to GitHub: `git push origin compiler-fix-working`
2. Create GitHub Issues for PATCH 4-6
3. Hire cheap helper for PATCH 4 (est. cost: $10-12)
4. Review work, commit, validate
5. Repeat for PATCH 5 and 6
6. Run 52 regression tests
7. Pull request to main

## BUDGET

- Available: $200 (two $100 keys)
- Spent: $0
- Estimated remaining: $130-160
- Reserve: $40-70

## HELPERS NEEDED

- PATCH 4: gpt-4o-mini ($10-12) - Caller PC
- PATCH 5: claude-haiku ($8-12) - Loop fixpoint
- PATCH 6: gpt-4o-mini ($8-12) - Branch merge
- Docs: claude-haiku ($5-10) - Threat model

## SUCCESS CRITERIA

When complete:
- [x] 50% patches done (3/6)
- [ ] 100% patches done (6/6)
- [ ] 52/52 regression tests pass
- [ ] Threat model written
- [ ] Ready for commercial MVP

---

**Session:** Cline (2026-10-11)  
**Commits:** 4 new  
**Status:** CHECKPOINT COMPLETE ✅
