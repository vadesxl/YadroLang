# Нативный ABI v1

Yadro Guard генерирует C-compatible collision-resistant symbols:

- пользовательские функции: `yadro_fn_<readable>_<sha256-prefix>`
- policy/runtime функции: `yadro_abi_v1_<readable>_<sha256-prefix>`
- process entry: `main`

Readable-часть служит диагностике; 16 hex SHA-256 связывает полное UTF-8 имя. Параметры и возвраты используют выведенные LLVM scalar types. Policy sources/sinks/sanitizers сейчас возвращают signed i64.

Один external source name имеет одну сигнатуру на модуль. Несовместимость блокируется CodeGen. Native smoke компилирует Yadro, создаёт объектник, линкует C runtime stubs, запускает binary и проверяет результат на Ubuntu, Windows и macOS.

Runtime stubs являются тестами, а не trusted sanitizer. Деклассификация остаётся compile-time policy решением.
