# Yadro Guard MCP security manifest v1.0

Это **собственная статическая security-схема Yadro Guard**, а не универсальный импорт любого MCP server config.

Корневые поля: `version`, `tools`, `flows`. Неизвестные поля отклоняются. Tool содержит уникальное `name`, `labels`, `sanitizes`, `capabilities`.

Метки: ПДн, Финансы, Здоровье, УчетныеДанные, Локация.
Capabilities: ДоступСети, ЗаписьДиска, ЗаписьБД, ЧтениеБД, ВыполнениеИнструмента, ДоступСекретов, ДоступЛог.

Flows задаются рёбрами `[source, target]`. Циклы поддерживаются bounded fixpoint конечной решётки. Результат детерминирован и доступен как text, JSON или SARIF 2.1.0. Неизвестные tools, edges, labels, capabilities, duplicate tools и fields отклоняются.
