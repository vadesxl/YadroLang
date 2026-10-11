# GitHub Setup для работы с дешевыми помощниками

## ✅ Локальная подготовка (DONE)

- [x] Клонирована обе ветки (YadroLang + YadroLang-English)
- [x] Созданы рабочие ветки: `compiler-fix-working`
- [x] Установлена Python 3.11+
- [x] Установлены зависимости: `pip install -r requirements.txt`
- [x] Синтаксис validated: `python -m py_compile src/этика_v21_patched.py`
- [x] Тесты written и passing: `test_patches_quick.py`

## 🔄 GitHub подключение (TODO)

### Шаг 1: Проверить credentials
```bash
git config --global user.name "vadesxl"
git config --global user.email "39384856+vadesxl@users.noreply.github.com"
git remote -v
```

### Шаг 2: Push текущие изменения
```bash
git push origin compiler-fix-working
```

### Шаг 3: Создать GitHub Issues для patches 4-6

**Issue #1: PATCH 4 - Caller PC into callee summaries**
- Title: `[compiler-fix] PATCH 4: Caller PC context propagation`
- Labels: `compiler`, `taint-analysis`, `security`
- Root Cause: Helper functions don't inherit caller's control context

**Issue #2: PATCH 5 - Loop fixpoint including condition taint**
- Title: `[compiler-fix] PATCH 5: Loop condition taint in fixpoint`
- Labels: `compiler`, `loops`, `security`

**Issue #3: PATCH 6 - Branch-merge sanitizer fix**
- Title: `[compiler-fix] PATCH 6: Preserve post-branch sanitization`
- Labels: `compiler`, `sanitizers`, `security`

## 🤖 Cheap Models Setup

### Вариант 1: Claude (Recommended - cheapest)
- Model: claude-3-5-haiku ($0.80/$2.40 per 1M tokens)
- Use for: Docs, simple patches, tests

### Вариант 2: OpenAI GPT-4o-mini
- Cost: $0.15/$0.60 per 1M tokens
- Use for: Complex patches, validation

### Бюджет
```
Account 1: $100 (spent $0, remaining $100)
Account 2: $100 (backup for later)
Total MVP cost estimate: $40-60
```

## ✅ Pre-GitHub Checklist

- [ ] Git credentials configured
- [ ] Can push to origin
- [ ] compiler-fix-working branch ready
- [ ] API key for first helper task ready
- [ ] Budget tracking setup
- [ ] Ready to create GitHub Issues

---

**Status:** Ready for GitHub integration ✅  
**Next:** Push to origin and create Issues for remaining patches
