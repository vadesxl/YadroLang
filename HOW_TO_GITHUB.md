# How to Use GitHub + Cheap Helpers

## 1. Push Current Work

```bash
cd E:\загрузки\.gemini\antigravity\scratch\YadroLang
git push origin compiler-fix-working
```

Creates branch on GitHub with all our patches.

## 2. Create GitHub Issues

Go to https://github.com/vadesxl/YadroLang/issues/new

**Issue 1: PATCH 4 - Caller PC**
```
Title: [compiler-fix] PATCH 4: Caller PC context propagation
Labels: compiler, taint-analysis, security
Body:
Root cause: Helper functions don't inherit caller's control context

What to do:
1. Read docs/analysis/flow-gaps.md section 4
2. Modify src/этика_v21_patched.py
3. Run: python test_patches_quick.py
```

**Issue 2: PATCH 5 - Loop fixpoint**
**Issue 3: PATCH 6 - Branch merge**

## 3. Hire Cheap Helper

### Option A: OpenAI (Recommended)
1. Get API key from platform.openai.com
2. Create `.env` file:
```
OPENAI_API_KEY=sk-...
```
3. Use model: `gpt-4o-mini`
4. Cost: ~$0.15 per 1M tokens

### Option B: Claude
1. Get API key from console.anthropic.com
2. Create `.env` file:
```
ANTHROPIC_API_KEY=sk-ant-...
```
3. Use model: `claude-3-5-haiku`
4. Cost: ~$0.80 per 1M tokens

## 4. Give Task to Helper

### Template

**Subject:** `PATCH 4: Implement Caller PC into Callee Summaries`

**Message:**
```
Context:
- Branch: compiler-fix-working
- File: src/этика_v21_patched.py
- Root cause: See docs/analysis/flow-gaps.md section 4

Task:
Modify _суммировать_утечки() to propagate caller's pc_метки 
into helper function summaries.

Current code (line 182-188):
  def _суммировать_утечки(self, функция):
      утечки = set()
      for индекс, параметр in enumerate(функция.параметры):
          for метка in ВСЕ_МЕТКИ:
              if self._тело_утекает(функция.тело, {параметр: {метка}}, set()):
                  утечки.add((индекс, метка))
      return утечки

What needs to change:
- Pass caller's pc_метки to _тело_утекает
- Track control-flow dependent taint in helper context

Validation:
python -m py_compile src/этика_v21_patched.py
python test_patches_quick.py  # Should pass 3/3

Submit:
- Updated src/этика_v21_patched.py
- Commit message: "feat: PATCH 4 - caller PC into summaries"
- Any new tests (optional)

Budget: $8-12
```

## 5. Review Helper's Work

Steps:
1. Download the modified file
2. Run: `python test_patches_quick.py`
3. Check: syntax valid? Tests pass?
4. If OK: commit to git
5. If issues: ask helper to fix, don't push broken code

## 6. Commit Helper's Work

```bash
git add src/этика_v21_patched.py
git commit -m "feat: PATCH 4 - caller PC into summaries"
git push origin compiler-fix-working
```

## 7. Validate Against Regression Suite

Get tests from semantic-analysis branch:
```bash
git checkout origin/agent/semantic-analysis -- tests/
```

Run full suite:
```bash
python -m pytest tests/test_ethics_v21.py -v
```

Expected: Most should fail until PATCH 6 is done.

## 8. Repeat for PATCH 5 and 6

Same process:
- Create issue
- Hire helper
- Review work
- Commit
- Validate
- Move to next

## 9. Final Validation

When all 6 patches done:
```bash
python -m pytest tests/ -v
# Should see significant improvement in pass rate
```

## 10. Create Pull Request

Go to GitHub, click "Pull Request"

- From: `compiler-fix-working`
- To: `agent/compiler-fix` (or main if ready)

Title: `feat: Complete compiler-fix phase - 6 patches applied`

## Troubleshooting

**Q: Test fails after helper's work?**  
A: Tell helper to review flow-gaps.md more carefully

**Q: Can't find regression tests?**  
A: They're in agent/semantic-analysis branch, fetch them

**Q: Git push fails?**  
A: Check credentials, might need Personal Access Token

**Q: Helper cost too high?**  
A: Use cheaper model (claude-haiku) or break task into smaller parts

---

**Total expected cost for 3 patches:** $25-35
**Timeline:** ~1 week
**Ready:** YES ✅
