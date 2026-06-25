# -*- coding: utf-8 -*-
"""Генератор LLVM IR для YadroLang (через llvmlite).

Поддержка: функции, if/while, рекурсия, встроенная 'печать' (printf),
автогенерация нативной точки входа main для запуска как ELF-бинаря.
"""
from llvmlite import ir, binding as llvm
from src.синтаксис import (Программа, Функция, Вернуть, Пусть, Присвоить,
                           Если, Пока, Число, Строка, Имя, Бинарный, Вызов)

ЦЕЛОЕ = ir.IntType(64)
БУЛЕВ = ir.IntType(1)
БАЙТ = ir.IntType(8)
УКАЗ = БАЙТ.as_pointer()
I32 = ir.IntType(32)


class ОшибкаКодогена(Exception):
    ...


class Кодоген:
    def __init__(self):
        self.модуль = ir.Module(name="ядро")
        self.модуль.triple = llvm.get_default_triple()
        self.функции = {}
        self.строитель = None
        self.скоуп = {}
        self._счёт = 0
        printf_ty = ir.FunctionType(I32, [УКАЗ], var_arg=True)
        self.printf = ir.Function(self.модуль, printf_ty, name="printf")

    def _строка_глоб(self, текст):
        данные = bytearray(текст.encode("utf-8") + b"\x00")
        тип = ir.ArrayType(БАЙТ, len(данные))
        г = ir.GlobalVariable(self.модуль, тип, name=f".str.{self._счёт}")
        self._счёт += 1
        г.linkage = "internal"
        г.global_constant = True
        г.initializer = ir.Constant(тип, данные)
        return г

    def _указ(self, b, г):
        ноль = ir.Constant(I32, 0)
        return b.gep(г, [ноль, ноль], inbounds=True)

    def сгенерировать(self, прог: Программа) -> str:
        self._фмт_число = self._строка_глоб("%lld\n")
        self._фмт_рез = self._строка_глоб("Результат старт(): %lld\n")
        for ф in прог.функции:
            тип = ir.FunctionType(ЦЕЛОЕ, [ЦЕЛОЕ] * len(ф.параметры))
            self.функции[ф.имя] = ir.Function(self.модуль, тип, name=ф.имя)
        for ф in прог.функции:
            self._функция(ф)
        if "старт" in self.функции:
            self._главная()
        return str(self.модуль)

    def _главная(self):
        fn = ir.Function(self.модуль, ir.FunctionType(I32, []), name="main")
        b = ir.IRBuilder(fn.append_basic_block("вход"))
        рез = b.call(self.функции["старт"], [])
        b.call(self.printf, [self._указ(b, self._фмт_рез), рез])
        b.ret(ir.Constant(I32, 0))

    def _функция(self, ф: Функция):
        fn = self.функции[ф.имя]
        блок = fn.append_basic_block("вход")
        self.строитель = ir.IRBuilder(блок)
        self.скоуп = {}
        for арг, имя in zip(fn.args, ф.параметры):
            арг.name = имя
            ячейка = self.строитель.alloca(ЦЕЛОЕ, name=имя)
            self.строитель.store(арг, ячейка)
            self.скоуп[имя] = ячейка
        for утв in ф.тело:
            self._утверждение(утв)
        if not self.строитель.block.is_terminated:
            self.строитель.ret(ЦЕЛОЕ(0))

    def _утверждение(self, у):
        if isinstance(у, Вернуть):
            self.строитель.ret(self._выражение(у.значение))
        elif isinstance(у, Пусть):
            ячейка = self.строитель.alloca(ЦЕЛОЕ, name=у.имя)
            self.строитель.store(self._выражение(у.значение), ячейка)
            self.скоуп[у.имя] = ячейка
        elif isinstance(у, Присвоить):
            if у.имя not in self.скоуп:
                raise ОшибкаКодогена(f"Переменная '{у.имя}' не объявлена (строка {у.строка})")
            self.строитель.store(self._выражение(у.значение), self.скоуп[у.имя])
        elif isinstance(у, Если):
            self._если(у)
        elif isinstance(у, Пока):
            self._пока(у)
        else:
            self._выражение(у)

    def _если(self, у: Если):
        усл = self._в_булев(self._выражение(у.условие))
        с_иначе = bool(у.иначе)
        bb_тогда = self.строитель.append_basic_block("тогда")
        bb_иначе = self.строитель.append_basic_block("иначе") if с_иначе else None
        bb_конец = self.строитель.append_basic_block("конец_если")
        self.строитель.cbranch(усл, bb_тогда, bb_иначе or bb_конец)
        self.строитель.position_at_end(bb_тогда)
        for s in у.тогда:
            self._утверждение(s)
        if not self.строитель.block.is_terminated:
            self.строитель.branch(bb_конец)
        if с_иначе:
            self.строитель.position_at_end(bb_иначе)
            for s in у.иначе:
                self._утверждение(s)
            if not self.строитель.block.is_terminated:
                self.строитель.branch(bb_конец)
        self.строитель.position_at_end(bb_конец)

    def _пока(self, у: Пока):
        bb_усл = self.строитель.append_basic_block("усл_цикла")
        bb_тело = self.строитель.append_basic_block("тело_цикла")
        bb_выход = self.строитель.append_basic_block("выход_цикла")
        self.строитель.branch(bb_усл)
        self.строитель.position_at_end(bb_усл)
        self.строитель.cbranch(self._в_булев(self._выражение(у.условие)), bb_тело, bb_выход)
        self.строитель.position_at_end(bb_тело)
        for s in у.тело:
            self._утверждение(s)
        if not self.строитель.block.is_terminated:
            self.строитель.branch(bb_усл)
        self.строитель.position_at_end(bb_выход)

    def _выражение(self, в):
        if isinstance(в, Число):
            return ЦЕЛОЕ(в.значение)
        if isinstance(в, Имя):
            if в.имя not in self.скоуп:
                raise ОшибкаКодогена(f"Неизвестная переменная '{в.имя}' (строка {в.строка})")
            return self.строитель.load(self.скоуп[в.имя], name=в.имя)
        if isinstance(в, Бинарный):
            л = self._выражение(в.слева); п = self._выражение(в.справа)
            return {
                "+": lambda: self.строитель.add(л, п),
                "-": lambda: self.строитель.sub(л, п),
                "*": lambda: self.строитель.mul(л, п),
                "/": lambda: self.строитель.sdiv(л, п),
                ">": lambda: self.строитель.icmp_signed(">", л, п),
                "<": lambda: self.строитель.icmp_signed("<", л, п),
                "==": lambda: self.строитель.icmp_signed("==", л, п),
            }[в.оп]()
        if isinstance(в, Вызов):
            if в.имя == "печать":
                узел = в.аргументы[0]
                if isinstance(узел, Строка):
                    г = self._строка_глоб(узел.значение)
                    self.строитель.call(self.printf,
                        [self._указ(self.строитель, self._фмт_строка),
                         self._указ(self.строитель, г)])
                else:
                    арг = self._выражение(узел)
                    self.строитель.call(self.printf,
                        [self._указ(self.строитель, self._фмт_число), арг])
                return ЦЕЛОЕ(0)
            if в.имя not in self.функции:
                raise ОшибкаКодогена(f"Неизвестная функция '{в.имя}' (строка {в.строка})")
            арг = [self._выражение(a) for a in в.аргументы]
            return self.строитель.call(self.функции[в.имя], арг)
        raise ОшибкаКодогена(f"Не могу сгенерировать узел {type(в).__name__}")

    def _в_булев(self, знач):
        if знач.type == БУЛЕВ:
            return знач
        return self.строитель.icmp_signed("!=", знач, ЦЕЛОЕ(0))
