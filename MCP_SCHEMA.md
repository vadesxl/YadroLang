# Схема Yadro MCP tool graph v1.0

Это собственная схема анализа Yadro, не универсальный импорт всех MCP manifest.

```json
{"version":"1.0","tools":[{"name":"crm.читать","labels":["ПДн"]},{"name":"сеть.отправить","capabilities":["ДоступСети"]}],"flows":[["crm.читать","сеть.отправить"]]}
```

Tool может иметь `labels`, `sanitizes`, `capabilities`. `flows` содержит направленные пары имён. Сканер проверяет дубли и неизвестные tools, вычисляет bounded fixpoint на циклах, блокирует чувствительные данные у privileged capabilities и отмечает три и более опасных capability как excessive agency.
