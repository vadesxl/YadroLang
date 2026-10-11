# GitHub Quick Start для Cline

## В двух словах

1. **Создай GitHub Token** → https://github.com/settings/tokens/new
2. **Установи GitHub MCP** → `npm install -g @modelcontextprotocol/server-github`
3. **Установи переменную** → `$env:GITHUB_TOKEN = "ghp_..."`
4. **Нужна поддержка в Aider/Cline** для MCP
5. **Done!** Я смогу работать с GitHub напрямую

## Почему MCP?

Без MCP: Ты даешь мне команды → я говорю что сделать → ты вручную делаешь

С MCP: Я делаю все сам → создаю Issues → делаю commits → pushю → создаю PRs

## Пошаговая инструкция (5 минут)

### Шаг 1: Создать token (2 мин)
```
Go to: https://github.com/settings/tokens/new
Name: cline-yadro
Select:
  ✅ repo (полный доступ к репо)
  ✅ workflow (GitHub Actions)
  ✅ admin:repo_hook (hooks)
Click: Generate token
Copy & Save (показывается только один раз!)
```

### Шаг 2: Установить MCP (2 мин)
```powershell
# Если нет Node.js, установи:
winget install OpenJS.NodeJS

# Установи GitHub MCP
npm install -g @modelcontextprotocol/server-github
```

### Шаг 3: Установить token (1 мин)
```powershell
# Временно (текущая сессия):
$env:GITHUB_TOKEN = "ghp_YOUR_TOKEN_HERE"

# Постоянно (добавь в профиль):
notepad $PROFILE
# Добавь строку:
# $env:GITHUB_TOKEN = "ghp_YOUR_TOKEN_HERE"
# Сохрани и перезагрузи PowerShell
```

## Что станет возможно

### С MCP я смогу:

✅ **Создавать Issues**
- Автоматически создам Issues для PATCH 4, 5, 6
- Буду обновлять статус в Issues

✅ **Делать Commits**
- Буду коммитить patches напрямую
- Писать правильные commit messages

✅ **Pushить в GitHub**
- Автоматически отправлять изменения
- Создавать Pull Requests

✅ **Читать Issues**
- Получать feedback от helpers
- Обновлять Issues с результатами

### Примеры что я смогу сделать:

```
@cline: Create GitHub issue for PATCH 4
Title: [compiler-fix] PATCH 4: Caller PC context
Labels: compiler, security, taint-analysis
Body: 
  Root cause: Helpers don't inherit caller PC
  See: docs/analysis/flow-gaps.md section 4
```

```
@cline: Commit and push patches 1-3 to GitHub
Message: "feat: apply patches 1-3 - output sink + pc_metki propagation"
Branch: compiler-fix-working
```

```
@cline: Create pull request
From: compiler-fix-working
To: agent/compiler-fix
Title: "feat: apply patches 1-3"
Description: "3 security patches applied and validated"
```

## Альтернатива (без MCP)

Если MCP сложно, можем использовать **GitHub CLI**:

```bash
# Установить
winget install GitHub.cli

# Авторизация
gh auth login

# Потом я смогу использовать:
gh issue create --title "..." --body "..."
gh pr create --base agent/compiler-fix --head compiler-fix-working
```

## Проверка что работает

Когда MCP установлен, я смогу ответить на:
```
@cline: List recent issues in this repo
@cline: Show status of compiler-fix-working branch
@cline: Check if I have access to push
```

Если ответы есть - все работает!

## Что дальше

1. ✅ **Setup MCP** (5 минут)
2. ✅ **Test connection** (2 минуты)
3. 🚀 **Start automated workflow:**
   - Я создаю Issues
   - Ты нанимаешь helpers по Issues
   - Helpers делают work
   - Я интегрирую изменения
   - Я pushю в GitHub
   - Все автоматически обновляется

## Risotto

Если что-то не работает:
- Check: `$env:GITHUB_TOKEN` - должен быть установлен
- Check: `npm list -g @modelcontextprotocol/server-github` - должен быть installed
- Check: GitHub token не expired (valid for 30+ days)
- Fallback: Используй GitHub CLI вместо MCP

---

**Time needed:** 5 minutes  
**Difficulty:** Easy  
**Payoff:** 100% automation of GitHub workflow  
**Status:** READY TO SETUP ✅
