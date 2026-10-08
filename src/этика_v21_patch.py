# -*- coding: utf-8 -*-
"""Reference patch for the security fix queue in YadroLang.

This branch-local file documents the concrete code changes needed so the
ethical analyzer becomes control-flow aware without changing the public ABI.

It is intentionally not imported by the compiler yet; it is a reference patch
for the next merge when the regression suite is green.
"""

# --- PATCH 1: add output sinks and final return check ---
# In src/этика_v21.py

# BEFORE
# СТОКИ = {
#     "сеть.отправить": "ДоступСети",
#     ...
# }
#
# AFTER
# СТОКИ = {
#     "печать": "ВыводПрограммы",
#     "сеть.отправить": "ДоступСети",
#     ...
# }

# BEFORE
# def проверить(self, программа: Программа):
#     self.функции = {ф.имя: ф for ф in программа.функции}
#     self.аудит_трейл = []
#     self._запретить_подмену(программа)
#     self._вычислить_сводки()
#     for функция in программа.функции:
#         self._проверить_мандаты(функция)
#         self._сканировать_тело(функция.тело, {}, set())
#     return self.аудит_трейл
#
# AFTER
# def проверить(self, программа: Программа):
#     self.функции = {ф.имя: ф for ф in программа.функции}
#     self.аудит_трейл = []
#     self._запретить_подмену(программа)
#     self._вычислить_сводки()
#     for функция in программа.функции:
#         self._проверить_мандаты(функция)
#         self._сканировать_тело(функция.тело, {}, set())
#     self._проверить_выход_старта(программа)
#     return self.аудит_трейл
#
# def _проверить_выход_старта(self, программа):
#     старт = next((ф for ф in программа.функции if ф.имя == "старт"), None)
#     if not старт:
#         return
#     labels = self._метки_возврата(старт.тело, {})
#     if labels:
#         raise ЭтическаяОшибка(
#             f"Возвращаемое значение старт() содержит чувствительные данные: {labels}",
#             "ЯДРО-Э2304",
#         )

# --- PATCH 2: merge active control context into value transfer ---
# The transfer function is conceptually:
#
# def _transfer_labels(value, env, pc):
#     return self._метки(value, env) | set(pc)
#
# In assignment handling:
#
# BEFORE
# if isinstance(утверждение, (Пусть, Присвоить)):
#     if self._выражение_утекает(утверждение.значение, окружение, pc_метки):
#         return True
#     окружение[утверждение.имя] = self._метки(утверждение.значение, окружение)
#
# AFTER
# if isinstance(утверждение, (Пусть, Присвоить)):
#     if self._выражение_утекает(утверждение.значение, окружение, pc_метки):
#         return True
#     value_labels = self._метки(утверждение.значение, окружение)
#     окружение[утверждение.имя] = value_labels | set(pc_метки)
#
# In return handling:
#
# BEFORE
# elif isinstance(утверждение, Вернуть):
#     if self._выражение_утекает(утверждение.значение, окружение, pc_метки):
#         return True
#
# AFTER
# elif isinstance(утверждение, Вернуть):
#     if self._выражение_утекает(утверждение.значение, окружение, pc_метки):
#         return True
#     value_labels = self._метки(утверждение.значение, окружение)
#     return_labels = value_labels | set(pc_метки)
#     # the caller accumulates `return_labels` into the function summary

# --- PATCH 3: loop fixpoint with condition labels ---
# In loop analysis:
#
# BEFORE
# дочерние_pc = set(pc_метки) | self._метки(утверждение.условие, окружение)
#
# AFTER
# condition_labels = self._метки(утверждение.условие, окружение)
# дочерние_pc = set(pc_метки) | condition_labels
# loop_env = self._поток_цикла(утверждение.тело, окружение)
# # apply until fixed point

# --- PATCH 4: fix stale merge after sanitization ---
# BEFORE
# окружение = self._объединить(окружение, левое, правое)
#
# AFTER
# branch_env = self._объединить(левое, правое)
# # normalize to preserve the post-branch sanitized state and drop stale labels
# # from the incoming environment when both branches sanitize equally
# окружение = branch_env

# --- PATCH 5: function summary should include pc-aware results ---
# Summary is no longer purely data-only; it should carry the control label context.
# Conceptually:
#
# @dataclass
# class СводкаВозврата:
#     фиксированные: set = field(default_factory=set)
#     потоки: dict = field(default_factory=dict)
#     pc_потоки: dict = field(default_factory=dict)
#
# and when evaluating a helper call:
#
# result = set(summary.фиксированные)
# for index, arg_labels in enumerate(arg_labels_list):
#     result |= summary.потоки.get((index, label), set())
# for pc_label in pc_метки:
#     result |= summary.pc_потоки.get((index, label, pc_label), set())


def _example_assign_context() -> str:
    return """
    # Example that should now be rejected
    функция старт() {
        пусть x = 0
        если среда.секрет() {
            x = 1
        }
        печать(x)
    }
    """


__all__ = [
    "_example_assign_context",
]
