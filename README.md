# YadroLang (ЯДРО) 2.1.0

[![CI](https://github.com/vadesxl/YadroLang/actions/workflows/run.yml/badge.svg)](https://github.com/vadesxl/YadroLang/actions/workflows/run.yml)
[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](pyproject.toml)
[![License](https://img.shields.io/badge/license-GPL--3.0--only-green.svg)](LICENSE)

> «Код это закон. Добро это выбор».

YadroLang является экспериментальным русскоязычным системным языком для проверяемого программирования AI-агентов и MCP tool graph. Он компилируется через LLVM в нативный объектный код: без VM, интерпретатора и сборщика мусора в runtime.

**Статус:** исследовательский прототип. Версия 2.1.0 не заявляется как production-ready, формально полная или неуязвимая.

## Что реально реализовано в 2.1.0

- русские ключевые слова, функции, переменные, рекурсия, `если/иначе`, `пока` и `вернуть`;
- вывод типов `ц64`, `bool` и ограниченных строковых значений;
- LLVM IR, его проверка и нативные object files для Linux, macOS и Windows;
- compile-time capability mandates для чувствительных системных API;
- межпроцедурный multi-label taint-анализ, implicit-flow/PC labels и строгая declassification;
- CLI `scan`, `audit`, `compile`, JSON, SARIF и versioned custom policy;
- bounded-анализ Yadro MCP tool graph;
- внешний ABI v1 со стабильными хэшированными символами;
- unsigned Proof Seal v1 как библиотечная модель и bounded offline verifier.

Proof Seal подтверждает внутреннюю согласованность записанного evidence. Он **не** доказывает его полноту, происхождение или подлинность и не заменяет подпись. `inspect_bytes` не является security gate. Подробнее: [PROOF_SEAL.md](PROOF_SEAL.md) и [PROOF_SEAL_IMPLEMENTATION.md](PROOF_SEAL_IMPLEMENTATION.md).

## Конвейер

```text
.яд -> Lexer -> Parser/AST -> semantics/types -> Ethical Checker -> LLVM IR verify -> native object
```

Слои Proof Seal пока не подключены к полному compiler pipeline и CLI. Source byte spans, compiler evidence export, LLVM/object binding и authenticated envelope остаются отдельными этапами.

## Пример

```yadro
функ удвоить(значение) {
    вернуть значение * 2
}

функ старт() {
    печать(удвоить(21))
    вернуть 0
}
```

## Быстрый старт

Требования: Python 3.11+, `llvmlite==0.43.0`; для Windows native object требуется поддерживаемый LLVM/Clang toolchain.

```bash
git clone https://github.com/vadesxl/YadroLang.git
cd YadroLang
python -m pip install -e .

python -m src.guard version
python -m src.guard scan examples/безопасный.яд
python -m src.guard audit examples/безопасный.яд
python -m src.guard compile examples/тест.яд --ir
python -m src.guard compile examples/тест.яд -o ядро.o
```

Полный контракт CLI и exit codes: [CLI.md](CLI.md). Статус возможностей: [FEATURE_STATUS.md](FEATURE_STATUS.md). ABI: [ABI.md](ABI.md).

## Модель Ethical Checker

Опасные sinks требуют объявленной capability. Чувствительные метки распространяются через значения, вызовы, возвраты и управляющий поток. Разрешённый sanitizer снимает только явно заявленные метки. Неизвестные или недоказанные переходы должны блокироваться, а не считаться безопасными.

Это статическая versioned policy model, а не универсальное доказательство «этичности». Она не покрывает произвольный native/FFI-код, malicious compiler, supply-chain compromise, runtime memory corruption, microarchitectural side channels и ошибки в самой policy.

## Честные ограничения

- текущая string реализация использует переходный pointer-only `%s` lowering и не является полной memory-safe string model;
- нет GC, VM, полного ownership, dynamic policy или произвольного MCP manifest import;
- unsigned Proof Seal не обеспечивает authenticity/provenance;
- consistency записанных call sites не доказывает completeness;
- защита должна рассматриваться как defense in depth, а не абсолютная граница;
- новые security claims принимаются только вместе с воспроизводимым adversarial test.

План string memory model: [STRING_MEMORY_MODEL.md](STRING_MEMORY_MODEL.md) появится в `main` после отдельного review и merge. Checked arithmetic также развивается отдельным opt-in профилем и не считается частью `main`, пока соответствующий PR не принят.

## Тестирование

CI проверяет unit, native, wheels, build и benchmark на Ubuntu, macOS и Windows. Security/native проверки не должны становиться зелёными через `skip`; отсутствие обязательного toolchain считается ошибкой.

```bash
python -m unittest discover -s tests -v
python -m benchmarks.run
```

## Security

Обход защиты считается дефектом, а не «неправильным использованием». Полезный отчёт должен содержать минимальный воспроизводимый input, ожидаемый и фактический результат, версию/commit и модель угроз. Не публикуйте реальные секреты или персональные данные в issue.

Приоритет аудита: parser/AST direct construction, Unicode и canonicalization, integer bounds, FFI assumptions, LLVM poison/ABI mismatches, evidence omission, resource exhaustion, malformed object formats и различия поведения между ОС.

## Лицензия

GPL-3.0-only. См. [LICENSE](LICENSE).
