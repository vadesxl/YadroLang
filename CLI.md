# Yadro Guard CLI

```bash
python -m src.guard version
python -m src.guard scan examples/тест.яд
python -m src.guard scan examples/утечка.яд --format json
python -m src.guard scan examples/утечка.яд --format sarif
python -m src.guard audit examples/безопасный.яд
python -m src.guard compile examples/тест.яд -o ядро.o
python -m src.guard policy check policies/example.json
```

## Exit codes

- `0`: успех
- `2`: нарушение политики
- `3`: ошибка исходника, синтаксиса, семантики, файла или формата policy
- `4`: внутренняя ошибка компилятора

## Policy format

JSON policy версии `1.0` добавляет sources, sinks и санитайзеры для конкретных меток. Метки ограничены встроенной конечной решёткой: `ПДн`, `Финансы`, `Здоровье`, `УчетныеДанные`, `Локация`.

SARIF соответствует версии 2.1.0 и подходит для загрузки в GitHub Code Scanning.
