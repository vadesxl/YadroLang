# -*- coding: utf-8 -*-
"""Компилятор YadroLang v1.0 - нативная компиляция через LLVM.

Использование:
    python -m src.main файл.яд          # компиляция в нативный объектник ядро.o
    python -m src.main файл.яд --ir     # вывести LLVM IR
"""
import sys
from llvmlite import binding as llvm
from src.лексер import Лексер
from src.синтаксис import Парсер
from src.этика import ЭтическийАнализатор
from src.кодоген import Кодоген


def компилировать(исходник: str, выводить_ir=False) -> str:
    токены = Лексер(исходник).токены()
    ast = Парсер(токены).разобрать()
    ЭтическийАнализатор().проверить(ast)   # закон до кода
    ir_код = Кодоген().сгенерировать(ast)
    if выводить_ir:
        print(ir_код)
    return ir_код


def собрать_нативно(ir_код: str, выход="ядро.o"):
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    модуль = llvm.parse_assembly(ir_код)
    модуль.verify()
    pmb = llvm.create_pass_manager_builder(); pmb.opt_level = 2
    pm = llvm.create_module_pass_manager(); pmb.populate(pm); pm.run(модуль)
    target = llvm.Target.from_default_triple().create_target_machine()
    with open(выход, "wb") as f:
        f.write(target.emit_object(модуль))
    print(f"[ЯДРО] Нативный объектник: {выход}")


def главная():
    if len(sys.argv) < 2:
        print("Использование: python -m src.main файл.яд [--ir]")
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        исходник = f.read()
    ir_код = компилировать(исходник, выводить_ir="--ir" in sys.argv)
    if "--ir" not in sys.argv:
        собрать_нативно(ir_код)
    print("[ЯДРО] Компиляция завершена. Код - это закон.")


if __name__ == "__main__":
    главная()
