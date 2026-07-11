# Паритет семантической поверхности

`spec/semantic_surface.json` является машиночитаемым контрактом публичной семантической поверхности русской и английской версий. Он охватывает нормализованные роли ключевых слов, категории AST, типы, роли встроенных функций, capabilities, семейства диагностик, команды CLI и exit codes. Локализованное написание намеренно не сравнивается.

Эта проверка **не доказывает** полную эквивалентность компиляторов, идентичный LLVM IR, одинаковый текст диагностик или поведенческое равенство всех программ. Для этого по-прежнему нужны парные fixtures и тесты компилятора.

## Два независимых сигнала

`snapshot-parity` является обязательной воспроизводимой проверкой. Она сравнивает текущий checkout с одним проверенным immutable commit второго репозитория и требует побайтового совпадения обеих копий `check_parity.py`. Green означает одинаковую объявленную поверхность конкретной пары snapshots, а не равенство двух live-веток `main`.

`pin-freshness` читает только metadata Git refs через `git ls-remote`; moving-branch code не загружается и не исполняется. Устаревший pin создает заметный warning, поэтому pin rot не остается скрытым, а security-sensitive parity result сохраняет воспроизводимость.

Оба checkout используют `persist-credentials: false`, workflow имеет только `contents: read`, Python 3.11 provisioned явно.

## Coordinated update runbook

1. Подготовить одинаковые изменения contract и validator в обоих репозиториях и локально проверить candidate pair.
2. Merge каждого contract PR разрешен только после обычной platform CI.
3. Открыть reciprocal pin-update PR с полученными immutable merge SHA.
4. Требовать `snapshot-parity` и обычные Linux, macOS, Windows checks на обоих pin PR.
5. Merge reciprocal pins и вручную запустить оба workflow. Последующий commit только в counterpart может снова вызвать freshness warning, не отменяя проверенную snapshot pair.

Никогда не заменять immutable counterpart ref движущейся веткой в `snapshot-parity`.
