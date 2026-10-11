# Подключение GitHub MCP для Cline

## Что такое MCP?

MCP (Model Context Protocol) - это стандарт для подключения AI агентов к внешним системам.
С GitHub MCP я смогу:
- Создавать Issues
- Делать commits и push
- Создавать Pull Requests
- Читать Issues и комментарии
- Работать с ветками напрямую

## Шаг 1: Создать GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens/new
2. Создай token с именем: `cline-yadro-compiler-fix`
3. Выдай права:
   - ✅ `repo` (full access to repositories)
   - ✅ `workflow` (manage GitHub Actions)
   - ✅ `admin:repo_hook` (manage repo hooks)
   - ✅ `project` (manage projects)

4. Скопируй token (будет виден только один раз!)
5. Сохрани в безопасном месте

## Шаг 2: Установить GitHub MCP Сервер

### Вариант A: Через npm (Рекомендуется)
```bash
npm install -g @modelcontextprotocol/server-github
```

### Вариант B: Через pip (Если используется Python)
```bash
pip install mcp-github
```

## Шаг 3: Настроить конфиг для Cline

Создай файл `mcp_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "node",
      "args": [
        "-e",
        "require('@modelcontextprotocol/server-github').cli(process.env.GITHUB_TOKEN)"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Замени `ghp_YOUR_TOKEN_HERE` на твой actual token.

## Шаг 4: Установить переменную окружения

### Windows PowerShell:
```powershell
$env:GITHUB_TOKEN = "ghp_YOUR_TOKEN_HERE"
```

### Windows CMD:
```cmd
set GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
```

### Постоянно (в профиле):
```powershell
# Открой $PROFILE файл
notepad $PROFILE

# Добавь строку:
$env:GITHUB_TOKEN = "ghp_YOUR_TOKEN_HERE"
```

## Шаг 5: Использовать MCP в работе

Когда подключено, я смогу:

### Создавать Issues прямо из Cline:
```
Task: Create GitHub issue for PATCH 4
- Title: [compiler-fix] PATCH 4: Caller PC context propagation
- Labels: compiler, security
- Body: [from flow-gaps.md]
```

### Делать commits и push:
```
Task: Commit patches 1-3 and push to GitHub
```

### Создавать Pull Requests:
```
Task: Create PR from compiler-fix-working to agent/compiler-fix
```

### Читать Issues и комментировать:
```
Task: Check issue #123 and update with progress
```

## Шаг 6: Тестировать подключение

Когда MCP настроен, попробуй:

```
@cline: Can you list GitHub issues for this repo?
```

Если работает, я должен вернуть список issues из YadroLang.

## Альтернатива: GitHub CLI + Git

Если MCP сложный, можем использовать GitHub CLI:

```bash
# Установить GitHub CLI
winget install GitHub.cli

# Или через Chocolatey
choco install gh

# Авторизация
gh auth login
```

Потом я смогу использовать `gh` команды через terminal.

## Что будет работать с MCP

### ✅ Сейчас можно делать:
- Создавать Issues
- Читать Issues
- Комментировать Issues
- Смотреть PRs
- Управлять ветками

### ⏳ Позже добавим:
- Автоматические commits (если поддерживает)
- CI/CD интеграция
- Release management

## Рекомендуемая установка

```bash
# 1. Установить Node.js (если еще нет)
winget install OpenJS.NodeJS

# 2. Установить GitHub MCP
npm install -g @modelcontextprotocol/server-github

# 3. Создать мокап конфига
echo '{
  "mcpServers": {
    "github": {
      "command": "node",
      "args": ["-e", "require('@modelcontextprotocol/server-github').cli(process.env.GITHUB_TOKEN)"],
      "env": {
        "GITHUB_TOKEN": "ghp_YOUR_TOKEN"
      }
    }
  }
}' > mcp_config.json

# 4. Сохранить токен в переменную окружения
```

## Безопасность

⚠️ **ВАЖНО:**
- Никогда не коммитить токен в GitHub!
- Использовать `.env` файл или environment variables
- Если токен скомпрометирован: https://github.com/settings/tokens -> Delete
- Создать новый токен с минимальными правами

## Дальнейшие шаги

Когда MCP подключен:

1. **Я смогу создавать Issues** для PATCH 4, 5, 6 автоматически
2. **Я смогу делать commits** из Cline напрямую
3. **Я смогу отправлять PR** с готовыми patches
4. **Я смогу управлять дешевыми помощниками** через Issues и комментарии

---

**Результат:** 100% автоматизация работы с GitHub! 🚀
