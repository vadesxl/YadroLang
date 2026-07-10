# Модель угроз Yadro Guard

## Активы
Чувствительные метки, policy-файлы, capability-графы AI/MCP, целостность компилятора, LLVM output и audit evidence.

## Границы доверия
Недоверенные исходники и JSON-схема Yadro MCP входят в доверенный анализатор. Custom policy расширяет встроенную политику, но проходит валидацию. LLVM и linker являются downstream trusted components.

## Возможности атакующего
Специально созданные исходники, глубокие выражения, рекурсия, malformed manifests, циклические графы, policy collisions, aliases, branch/loop side channels и подмена sanitizer.

## В области защиты
Явные и неявные потоки, confused deputy, excessive agency, malformed input, policy tampering через символы, compiler crashes, завершение анализа и поведение на трёх ОС.

## Вне области
Микроархитектурные side channels, вредоносный LLVM, runtime compromise после компиляции, корректность внешней реализации sanitizer и импорт произвольных MCP-форматов.

## Контроли
Конечная решётка меток, capability-мандаты, строгая деклассификация, bounded fixpoints, reserved symbols, строгие типы, LLVM verification, schema validation и детерминированные diagnostics.

## Остаточные риски
Runtime ABI library ещё не поставляется; sanitizer semantics требуют организационной гарантии; не все динамические i64 overflow проверяются; MCP поддерживает документированную схему Yadro.
