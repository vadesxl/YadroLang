# LLVM ABI v1

- User symbols: `yadro_fn_v1_*`.
- Entry implementation: `yadro_entry_v1_*`, внешний wrapper остаётся C `main`.
- External symbols: `yadro_ext_v1_*`.
- Хранение, аргументы и возвраты используют i64.
- Промежуточные сравнения используют i1 и расширяются на ABI-границах.
- Строки являются внутренними constant byte arrays и пока разрешены только в прямом `печать`.
- Один external policy symbol имеет одну arity на модуль.
