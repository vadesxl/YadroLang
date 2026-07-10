# Выводимая система типов YadroLang

YadroLang выводит `i64`, `bool` и `string` до LLVM. Арифметика требует `i64`, сравнения возвращают `bool`, присваивание не меняет тип. `если` и `пока` принимают `bool` и документированное legacy truthiness для `i64`. Типы параметров и возврата выводятся через вызовы и рекурсию. Mixed returns и unreachable statements отклоняются стабильными кодами `ЯДРО-Т2xxx`.

LLVM ABI v1 использует typed storage, стабильные хэшированные symbols, terminator-safe blocks и верифицирует каждый модуль.
