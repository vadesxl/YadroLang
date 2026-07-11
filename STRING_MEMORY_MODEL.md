# Модель памяти строк YadroLang v1

Статус: нормативный дизайн до реализации issue #31.

## Цели

`string` является неизменяемым UTF-8 view без сборщика мусора и скрытого выделения памяти. View не владеет байтами. Компилятор обязан доказать, что владелец жив дольше каждого использования view. Если доказательство невозможно, программа отклоняется.

Модель сохраняет ясный синтаксис языка: пользователь пишет обычные строковые значения, а lifetime и ABI проверяются статически.

## Представление

Логическое представление:

```text
string = { data: *const u8, len: u64 }
```

Инварианты:

- `len` измеряется в байтах, не в Unicode scalar values.
- `data` может быть null только при `len == 0`.
- Диапазон `[data, data + len)` должен быть читаемым весь lifetime view.
- Байты обязаны быть корректным UTF-8 при создании из безопасного YadroLang-кода.
- Нулевой терминатор не входит в контракт и не требуется.
- View неизменяем. Запись через `data` запрещена безопасным кодом.
- Сложение `data + len` проверяется на переполнение до dereference или FFI-вызова.

## Владельцы и provenance

В v1 существуют только явно классифицированные владельцы:

1. `static`: байты строкового литерала в read-only секции объектного файла. Lifetime равен времени жизни процесса.
2. `stack`: фиксированный буфер текущего frame, созданный будущим проверенным API. Lifetime заканчивается при выходе из frame.
3. `foreign-borrow`: память, переданная внешним API с документированным lifetime. Без такого контракта значение считается недоверенным и не может стать безопасным `string`.

Сам `string` всегда является borrow. Копирование view копирует только `(data, len)` и не продлевает lifetime владельца. Heap owner, reference counting, tracing GC и неявное копирование в v1 отсутствуют.

## Литералы

Строковый литерал понижается в LLVM private unnamed constant byte array без обязательного `\0`. View получает pointer на первый байт и точную UTF-8 длину. Одинаковые литералы могут быть объединены LLVM, поэтому identity адресов не является наблюдаемой семантикой.

Пустой литерал имеет `len == 0`; backend может использовать null или адрес стабильного zero-byte объекта. Код не вправе различать эти варианты.

## Stack storage и escape rules

Stack-backed view разрешен только пока жив frame владельца. Компилятор отклоняет:

- возврат stack-backed view;
- запись view в storage с большим lifetime;
- передачу во внешний API, который может сохранить pointer;
- слияние control-flow, если хотя бы один путь не доказывает достаточный lifetime;
- view, чей owner уничтожен или переиспользован.

Анализ выполняется по CFG после type checking и до LLVM CodeGen. Решетка provenance конечна: `static`, `stack(frame-id)`, `foreign(contract-id)`, `unknown`. `unknown` fail-closed отклоняется в любой escaping position.

## Возвраты и параметры

Первый реализуемый профиль намеренно строг:

- функции YadroLang могут принимать borrowed `string`;
- view действителен только на время вызова, если provenance не `static`;
- возврат `string` запрещен независимо от provenance до появления межпроцедурных lifetime summaries;
- сохранение параметра после возврата функции запрещено;
- рекурсивные вызовы не меняют lifetime входного borrow.

Даже возврат литерала сначала запрещен. Это сохраняет одно простое правило и не создает случайную специальную семантику до реализации summaries.

## FFI ABI v1

На границе с C строковый аргумент разворачивается в два скаляра в фиксированном порядке:

```c
const uint8_t *data, uint64_t len
```

Пара скаляров выбрана вместо C struct-by-value, чтобы не зависеть от target-specific правил возврата и классификации агрегатов. Имя external symbol по-прежнему связывает полную сигнатуру. `string` считается двумя ABI-аргументами, но одним аргументом языка.

FFI является явной границей доверия: компилятор доказывает корректность view только до входа во внешний код, а соблюдение `len`, read-only доступа и запрета retain обеспечивается проверенным ABI-контрактом и доверенной реализацией внешней функции.

Внешняя функция получает borrow только на время вызова. Retain запрещен по умолчанию. API, сохраняющий данные, обязан принимать копию через отдельный будущий owner API; одного capability-мандата недостаточно для ослабления memory safety.

Возврат строк из FFI в v1 запрещен. Будущий контракт обязан отдельно определить owner, destructor, UTF-8 validation, максимальную длину и поведение при null.

## LLVM lowering

Внутри модуля канонический тип:

```llvm
%yadro.string.v1 = type { ptr, i64 }
```

Для typed-pointer LLVM допускается эквивалент `{ i8*, i64 }`. Backend обязан:

- устанавливать host target triple и data layout до lowering;
- не использовать `inbounds getelementptr`, пока диапазон не доказан;
- сохранять `len` при phi/select и вызовах;
- не преобразовывать строку в C string без явной bounded copy;
- запускать `parse_assembly()` и `verify()` для итогового модуля;
- не добавлять `nonnull`, `dereferenceable` или `noalias` без доказательства инварианта.

Оптимизация не может менять lifetime. Lifetime intrinsics допустимы только как подсказки после проверки escape rules.

## Диагностики

Минимальный стабильный набор:

- `ЯДРО-М1-1001`: возврат string пока запрещен;
- `ЯДРО-М1-1002`: borrowed string переживает owner;
- `ЯДРО-М1-1003`: неизвестный foreign lifetime;
- `ЯДРО-М1-1004`: FFI пытается сохранить borrow;
- `ЯДРО-М1-1005`: недопустимая или переполненная длина.

Диагностика указывает источник owner, место создания view и escaping use. Ошибки относятся к source error, не к internal compiler error.

## Ethical Checker

Memory safety и этическая политика независимы и обе обязательны. Taint labels сопровождают весь view, а не pointer отдельно от length. Slice и передача через FFI сохраняют labels. Санитайзер может снять разрешенные labels, но не меняет provenance и не продлевает lifetime. Capability не разрешает dangling pointer.

## Обязательные тесты реализации

Этот design PR фиксирует нормативные ожидания и не заявляет прохождение runtime-тестов. Тесты распределены по следующим implementation PR:

### Фаза 1: literal view и bounded printing

1. LLVM shape: литерал понижается в `{ptr, i64}` с точной UTF-8 длиной.
2. Empty/null: пустая строка безопасна и не dereference null.
3. Embedded NUL: `"a\0b"` сохраняет длину 3 и не обрезается.
4. Unicode: длина считается в UTF-8 байтах.
7. Native: object, link и run обязательны на трех ОС, без skip.
9. Optimized IR: `-O2` сохраняет observable bytes и length.
10. Regression: текущая `печать("...")` остается рабочей, но использует bounded output, не `%s`.

### Фаза 2: stack provenance и escape analysis

5. Escape: возврат stack view отклоняется стабильным кодом.
8. Adversarial: `len` overflow и null с ненулевой длиной fail-closed.

### Фаза 3: foreign API и trust boundary

5. Escape: сохранение foreign borrow отклоняется стабильным кодом.
6. FFI: C stub получает точные pointer и length на Linux, macOS и Windows.
8. Adversarial: invalid UTF-8 на foreign boundary fail-closed.

## Не входит в v1

Mutable strings, concatenation, heap allocation, user-visible pointers, slices по Unicode-индексам, reference counting, GC и возврат owned strings. Они требуют отдельного owner API и не должны появляться как скрытая магия.
