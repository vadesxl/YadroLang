# GitHub Workflow для YadroLang

## Общая архитектура

Проект работает в **трех параллельных ветках**, каждая отвечает за свой аспект разработки:

```
main ← pull requests from:
├── agent/semantic-analysis  [COMPLETED] 52 regression tests + root-cause analysis
├── agent/compiler-fix       [ACTIVE]    patch queue + validation
└── agent/docs-release       [PREPARED]  threat model + honest release posture
```

## Текущий статус

| Ветка | Статус | Deliverables | Next |
|-------|--------|--------------|------|
| `agent/semantic-analysis` | ✅ DONE | 52 regression tests, flow-gaps.md | Archive as reference |
| `agent/compiler-fix` | 🔄 ACTIVE | Patches 1-3 applied | Validate + apply 4-6 |
| `agent/docs-release` | ⏳ PENDING | Threat model draft | Fill in findings |

## Работа в каждой ветке

### 1. `agent/semantic-analysis` (Семантический анализ)
**Цель:** Найти и задокументировать ВСЕ потенциальные пути утечки данных

**Deliverables:**
- `tests/test_ethics_v21.py` - Unit tests
- `docs/analysis/flow-gaps.md` - Root-cause analysis (7 confirmed gaps)
- 52 regression test cases

**Роль:** Это эталонный набор тестов. Компилятор должен отклонять все 52 случая.

### 2. `agent/compiler-fix` (Коррекция компилятора)
**Цель:** Применить patches для закрытия найденных дыр

**Patches (приоритет):**
1. ✅ `печать` as sink
2. ✅ PC-label propagation in assignments
3. ✅ PC-label propagation in returns
4. ⏳ Caller PC into callee summaries
5. ⏳ Loop fixpoint with condition taint
6. ⏳ Branch-merge sanitizer fix

**Файл:** `src/этика_v21_patched.py` (изолирован от основного)

**Валидация:** Каждый patch валидируется против регрессионного набора

### 3. `agent/docs-release` (Честная документация)
**Цель:** Написать правдивый threat model и release notes

**Содержит:**
- `THREAT_MODEL.md` - Что защищено, что не защищено
- `RELEASE_NOTES.md` - Что изменилось и почему
- `MIGRATION_GUIDE.md` - Как обновиться
- Policy examples для коммерческого MVP

## Помощники (Дешевые модели)

### Распределение ролей

```yaml
cline (主):
  - Стратегия и архитектура
  - Критические patches
  - Валидация качества
  - GitHub push/pull management

semantic-tester (claude-haiku или gpt-4o-mini):
  - Расширение regression suite
  - Поиск новых edge cases
  - Анализ gap coverage
  - Стоимость: LOW

compiler-patcher (gpt-4o-mini):
  - Применение patches 4-6
  - Синтаксис-fix
  - Локальная валидация
  - Стоимость: LOW

docs-keeper (claude-haiku):
  - Написание документации
  - Threat model analysis
  - Code comments
  - Стоимость: LOWEST
```

## Процесс коммита в GitHub

### 1. Локальная валидация
```bash
# Синтаксис проверка
python -m py_compile src/этика_v21_patched.py

# Быстрые тесты
python test_patches_quick.py

# Регрессионный набор (если есть)
python -m pytest tests/test_ethics_v21.py -v
```

### 2. Commit в локальную ветку
```bash
git add src/этика_v21_patched.py test_patches_quick.py
git commit -m "feat: apply patch X - [description]"
```

### 3. Push в GitHub
```bash
git push origin compiler-fix-working
```

### 4. Pull Request в основную рабочую ветку
- Описание: какой gap закрывает
- Тесты: пройденные и новые
- Статус: ready/draft/blocked

## Как использовать дешевые помощники

### Пример 1: Расширение regression suite
```
Task: "Добавь 10 новых regression test cases для loop + taint scenarios"
Model: gpt-4o-mini (claude-haiku)
Cost: ~$0.001-0.003
Input: flow-gaps.md + existing tests
Output: test_*.py files ready to commit
```

### Пример 2: Применение patch
```
Task: "Implement PATCH 4 - caller PC into callee summaries"
Model: gpt-4o-mini
Cost: ~$0.005-0.01
Input: flow-gaps.md section 4 + current code
Output: этика_v21_patched.py with patch applied
Validate: human runs test suite
```

### Пример 3: Документация
```
Task: "Write THREAT_MODEL.md section on implicit flows"
Model: claude-haiku
Cost: ~$0.001
Input: flow-gaps analysis
Output: markdown ready to commit
```

## Git Strategy

### Branch naming
- `compiler-fix-working` - текущая рабочая ветка
- `compiler-fix-patch-{N}` - изолированные patch branches (если нужны)
- `docs-release-{version}` - версионированные документы

### Commit messages
```
feat: краткое описание что добавили
fix: краткое описание что исправили  
docs: обновления документации
test: новые тесты или улучшения
chore: синтаксис, форматирование
```

## Dashboard / Tracking

Используй это для отслеживания прогресса:

```markdown
## Progress (2026-10-11)

### Patches Applied: 3/6
- [x] Patch 1: печать sink
- [x] Patch 2: PC assignments
- [x] Patch 3: PC returns
- [ ] Patch 4: Caller PC
- [ ] Patch 5: Loop fixpoint
- [ ] Patch 6: Branch merge

### Regression Tests: 0/52 validated
(Waiting for patches 4-6 before full run)

### Docs: 0/3
- [ ] THREAT_MODEL.md
- [ ] RELEASE_NOTES.md
- [ ] MIGRATION_GUIDE.md

### Budget: 100 USD spent / 100 USD remaining
```

## Когда запускать помощников

### ✅ Запускай помощников на:
- Расширение regression suite
- Применение простых patches
- Написание документации
- Поиск edge cases
- Форматирование кода

### ❌ НЕ запускай помощников на:
- Критические архитектурные решения
- Валидация регрессионного набора
- Merge в main
- Security decisions
- Финальная pull request

## Контрольный список перед merge в main

- [ ] Все 3 ветки готовы
- [ ] Все 6 patches applied и validated
- [ ] 52/52 regression tests pass
- [ ] THREAT_MODEL.md заполнен
- [ ] Нет TODO в коде
- [ ] Git history clean
- [ ] Code review пройден (себя перепроверь)
- [ ] CI passing (если есть)

## Смета на коммерческий MVP

**Timeline:** 2-3 недели  
**Бюджет:** ~$200 total  
- Semantic: $30
- Patches: $50  
- Docs: $20
- MVP: $100
- Reserve: $0

**Key milestones:**
- Week 1: All patches applied
- Week 2: Full validation + docs
- Week 3: Commercial CLI + policies
