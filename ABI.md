# Нативный ABI v1

Yadro Guard генерирует C-compatible collision-resistant symbols:

- пользовательские функции: `yadro_fn_<readable>_<sha256-prefix>`
- policy/runtime функции: `yadro_abi_v1_<readable>_<sha256-prefix>`
- process entry: `main`

Readable-часть служит диагностике; 16 hex SHA-256 связывает полное UTF-8 имя. Параметры и возвраты используют выведенные LLVM scalar types. Policy sources/sinks/sanitizers сейчас возвращают signed i64.

Один external source name имеет одну сигнатуру на модуль. Несовместимость блокируется CodeGen. Native smoke компилирует Yadro, создаёт объектник, линкует C runtime stubs, запускает binary и проверяет результат на Ubuntu, Windows и macOS.

## Windows toolchain contract

Windows native object generation требует поддерживаемый `clang` LLVM toolchain в `PATH`. Yadro передает проверенный LLVM IR в clang с host target triple, ограничивает object emission 30 секундами и отклоняет output без AMD64 COFF machine magic (`0x8664`). C linker и native smoke executable также имеют конечные timeout. Отсутствующий compiler является hard failure, тесты не пропускаются.

Установленный clang обязан принимать LLVM IR от установленной версии llvmlite. Version mismatch или timeout возвращается как контролируемая ошибка компиляции.

Runtime stubs являются тестами, а не trusted sanitizer. Деклассификация остается compile-time policy решением.
