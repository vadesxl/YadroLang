# Выводимая система типов YadroLang

YadroLang выводит `i64`, `bool` и `string` до LLVM. Арифметика требует `i64`, сравнения возвращают `bool`, присваивание не меняет тип. `если` и `пока` принимают `bool` и документированное legacy truthiness для `i64`. Типы параметров и возврата выводятся через вызовы и рекурсию. Mixed returns и unreachable statements отклоняются стабильными кодами `ЯДРО-Т2xxx`.

LLVM ABI v1 использует typed storage, стабильные хэшированные symbols, terminator-safe blocks и верифицирует каждый модуль.

## String safety profile v1

`string` является immutable borrowed view, а не владеющим объектом. Его pointer, byte length, provenance и lifetime проверяются по [STRING_MEMORY_MODEL.md](STRING_MEMORY_MODEL.md). До реализации межпроцедурных lifetime summaries возврат `string` запрещен; параметры разрешены только как borrow на время вызова. Taint labels сохраняются вместе со всем view и не влияют на memory lifetime.
