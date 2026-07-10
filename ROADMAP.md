# Коммерческая дорожная карта Yadro Guard

## Позиционирование

**Обещание:** до деплоя доказать, что AI-агент не отправит чувствительные данные и не вызовет привилегированные инструменты вне политики.

**Покупатель:** AI platform engineering, AppSec, compliance и команды регулируемых продуктов.

**Точка входа:** CI-сканер и policy compiler для MCP/agent tool graph. Runtime-конкуренты добавляют задержку, Yadro Guard даёт compile-time evidence без policy-overhead в hot path.

## 30-дневный MVP

### Неделя 1: надёжный компилятор
- Структурированные тесты и crash-proof диагностики.
- Межпроцедурные сводки с сохранением меток.
- Declassification с учётом метки и политики.
- Fuzzing Lexer/Parser, coverage и threat model.

### Неделя 2: продуктовый интерфейс
- CLI `yadro guard scan`.
- Версионированный YAML policy-файл для sources, sinks, labels, capabilities и sanitizers.
- JSON и SARIF для GitHub code scanning.
- Стабильные коды диагностик и machine-readable output.

### Неделя 3: интеграции AI-агентов
- Импорт MCP manifest и графа tool calls.
- Python/TypeScript adapters популярных agent frameworks.
- Три demo: утечка ПДн, утечка секрета, excessive agency.
- Подписанное audit evidence с версиями policy/compiler.

### Неделя 4: пилотный релиз
- Воспроизводимые бинарники Windows, Linux и macOS.
- Benchmarks, документация, примеры политик и migration guide.
- Бесплатный open-source CLI; платные team policies и on-prem enterprise.
- Найти 3 design partners: finance, healthcare, internal developer platforms.

## Гипотеза монетизации

- Community: бесплатный CLI и core policies.
- Team: EUR 499/месяц за CI, SARIF, общие политики и поддержку.
- Enterprise: от EUR 15k/год за on-prem, кастомные policy packs, SSO, audit retention и SLA.

## Не делать в MVP

Не клонировать Rust/C++, не строить package ecosystem и не расширять синтаксис ради синтаксиса. Коммерческое доказательство: заблокированные атаки агентов, низкий false-positive rate и аудит, которому доверяет покупатель.
