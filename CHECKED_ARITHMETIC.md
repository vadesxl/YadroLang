# Checked arithmetic profile v1

YadroLang сохраняет прежнюю signed i64 семантику по умолчанию. Optional profile включается только для компиляции:

```bash
yadro-guard compile program.яд --checked-arithmetic -o program.o
python -m src.main program.яд --checked-arithmetic
```

`scan` и `audit` не принимают flag: они не должны притворяться доказательством runtime overflow behavior.

## LLVM lowering

Checked `+`, `-`, `*` используют `llvm.sadd.with.overflow.i64`, `llvm.ssub.with.overflow.i64` и `llvm.smul.with.overflow.i64`. Overflow bit ведет в trap path. Checked `/` до `sdiv` проверяет divisor zero и пару `INT64_MIN / -1`.

Единый internal helper вызывает `llvm.trap` и заканчивается `unreachable`. Контракт не фиксирует signal text или одинаковый numeric exit code: гарантируется ненормальное завершение без продолжения вычисления.

Итоговый модуль проходит LLVM parse и verify. Профиль является instance-local CodeGen dependency, глобального переключателя нет.

## Constants, diagnostics и default profile

Диапазон литералов и постоянное опасное деление проверяются как раньше. Checked profile дополнительно отклоняет полностью вычислимый overflow add/sub/mul с кодом `ЯДРО-А1001` и source line. Неизвестный profile отклоняется кодом `ЯДРО-А1000`. Default profile не получает новую overflow-ошибку и не содержит overflow intrinsics или trap helper.

## Platform contract

Native tests обязательны на Linux, macOS и Windows. Они используют C ABI stubs для runtime values, проверяют безопасные add/sub/mul/div и ненормальное завершение для add/sub/mul overflow, division by zero и `INT64_MIN / -1`. Link и run имеют timeout; отсутствующий compiler является hard failure; Windows object обязан иметь AMD64 COFF magic. Numeric exit code не унифицируется между ОС, но trap не должен печатать нормальный result marker.

## Benchmark

`python -m benchmarks.run` выводит отдельные `compile` и `compile_checked` измерения с rounds, median и p95. Это воспроизводимый инженерный baseline, не hardware-independent обещание и не flaky release threshold. Числовой checked baseline будет зафиксирован только после накопления измерений на контролируемом runner.

## Ограничения

Профиль охватывает signed i64 operators текущего языка. Он не добавляет новый синтаксис, saturating arithmetic, пользовательские handlers или recovery после trap.
