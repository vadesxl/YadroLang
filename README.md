# YadroLang (ЯДРО) 2.1.0

[![CI](https://github.com/vadesxl/YadroLang/actions/workflows/run.yml/badge.svg)](https://github.com/vadesxl/YadroLang/actions/workflows/run.yml)
![Version](https://img.shields.io/badge/version-2.1.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)

> «Код это закон. Добро это выбор».

YadroLang — экспериментальный системный язык с русским синтаксисом для разработки проверяемых AI-компонентов. Компилятор строит LLVM IR и нативные объектные файлы без VM, интерпретатора и сборщика мусора в runtime.

## Что реально входит в 2.1.0

- функции, переменные, рекурсия, `если`/`иначе`, `пока` и `вернуть`;
- вывод и проверка типов `ц64`, `bool` и ограниченная поддержка строк;
- нативный LLVM backend и проверка итогового LLVM-модуля;
- capability-мандаты для чувствительных системных операций;
- межпроцедурный multi-label taint-анализ, включая неявные потоки через управление;
- строгая declassification через известные санитайзеры;
- JSON/SARIF CLI, пользовательские JSON-политики и анализ Yadro MCP tool graph;
- библиотечная модель Proof Seal и строгий bounded offline verifier;
- CI для Linux, macOS и Windows, включая обязательные native tests.

## Границы безопасности

YadroLang блокирует только формализованные нарушения в поддерживаемой семантике. Это не доказательство «этичности AI», не whole-program formal proof и не гарантия отсутствия уязвимостей.

Proof Seal 2.1.0 работает в unsigned-режиме: он проверяет внутреннюю целостность записанного evidence, но не подтверждает автора, provenance или полноту всех вызовов. `inspect_bytes` не является security gate. Интеграция evidence с полным compiler pipeline, source byte spans, binding к объектному файлу и authenticated envelope остаются отдельными фазами.

Текущий string backend использует переходный pointer-only `%s` lowering. Он не считается полноценной memory-safe моделью: embedded NUL, ownership и произвольное хранение/возврат строк пока не поддерживаются. Нормативный дизайн следующей модели описан отдельно.

## Конвейер

```text
.яд -> Лексер -> Парсер/AST -> Семантика и типы -> Ethical Checker
    -> LLVM CodeGen -> parse/verify -> native object
```

Компиляция прекращается при синтаксической, типовой, policy или LLVM-ошибке. Неизвестные чувствительные операции должны обрабатываться fail-closed в пределах поддерживаемой модели.

## Пример

```yadrolang
функ удвоить(значение) {
    вернуть значение * 2
}

функ старт() {
    печать(удвоить(21))
    вернуть 0
}
```

## Установка и запуск

Требования: Python 3.11+, `llvmlite==0.43.0`; для линковки нужен системный C/LLVM toolchain.

```bash
git clone https://github.com/vadesxl/YadroLang.git
cd YadroLang
python -m pip install -e .

# Проверить и получить LLVM IR
python -m src.main examples/тест.яд --ir

# Создать нативный объектный файл
python -m src.main examples/тест.яд

# Policy CLI
yadro-guard scan examples/безопасный.яд --format json
yadro-guard audit examples/безопасный.яд
yadro-guard-mcp scan path/to/tool-graph.json
```

## Ethical Checker

Опасный API требует явного capability-мандата, который проверяется по цепочке вызовов. Чувствительные данные получают метки (`ПДн`, `Финансы`, `Здоровье`, `УчётныеДанные`, `Локация`) и не могут попасть в запрещённый sink без разрешённого преобразования.

```yadrolang
функ экспорт(данные) требует [ДоступСети] {
    пусть безопасные = анонимизировать(данные)
    вернуть сеть.отправить(безопасные)
}
```

Это compile-time enforcement конкретной versioned policy, а не универсальный моральный классификатор.

## Документация

- [Статус возможностей](FEATURE_STATUS.md)
- [Архитектура](ARCHITECTURE.md)
- [Threat model](THREAT_MODEL.md)
- [CLI](CLI.md)
- [ABI](ABI.md)
- [Proof Seal](PROOF_SEAL.md)
- [Безопасность и сообщения об уязвимостях](SECURITY.md)
- [Roadmap](ROADMAP.md)

## Статус проекта

**Версия кода и пакета: 2.1.0. Статус: experimental.** Не объявлено: production readiness, полный ownership/string runtime, signed provenance, формальная полнота Ethical Checker или защита от всех side channels.

Лицензия: GPL-3.0-only.
