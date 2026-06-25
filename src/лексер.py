# -*- coding: utf-8 -*-
"""Лексер YadroLang. Превращает исходный текст в поток токенов с позициями."""
from enum import Enum, auto
from dataclasses import dataclass


class Вид(Enum):
    ЧИСЛО = auto(); СТРОКА = auto(); ИМЯ = auto()
    ФУНК = auto(); ВЕРНУТЬ = auto(); ПУСТЬ = auto()
    ЕСЛИ = auto(); ИНАЧЕ = auto(); ПОКА = auto()
    ИСТИНА = auto(); ЛОЖЬ = auto()
    ЛСКОБ = auto(); ПСКОБ = auto(); ЛФИГ = auto(); ПФИГ = auto()
    ЛКВАДР = auto(); ПКВАДР = auto()
    ЗАПЯТАЯ = auto(); ТОЧЗАП = auto()
    ПЛЮС = auto(); МИНУС = auto(); ЗВЕЗДА = auto(); СЛЕШ = auto()
    РАВНО = auto(); РАВНОРАВНО = auto(); БОЛЬШЕ = auto(); МЕНЬШЕ = auto()
    КОНЕЦ = auto()


КЛЮЧЕВЫЕ = {
    "функ": Вид.ФУНК, "вернуть": Вид.ВЕРНУТЬ, "пусть": Вид.ПУСТЬ,
    "если": Вид.ЕСЛИ, "иначе": Вид.ИНАЧЕ, "пока": Вид.ПОКА,
    "истина": Вид.ИСТИНА, "ложь": Вид.ЛОЖЬ,
}


@dataclass
class Токен:
    вид: Вид
    текст: str
    строка: int
    столбец: int


class ОшибкаЛексера(Exception):
    ...


class Лексер:
    def __init__(self, исходник: str):
        self.s = исходник
        self.i = 0
        self.строка = 1
        self.столбец = 1

    def _шаг(self) -> str:
        ch = self.s[self.i]; self.i += 1
        if ch == "\n":
            self.строка += 1; self.столбец = 1
        else:
            self.столбец += 1
        return ch

    def _взгляд(self, off=0) -> str:
        j = self.i + off
        return self.s[j] if j < len(self.s) else ""

    def токены(self):
        вывод = []
        while self.i < len(self.s):
            ch = self._взгляд()
            if ch in " \t\r\n":
                self._шаг(); continue
            if ch == "#":
                while self.i < len(self.s) and self._взгляд() != "\n":
                    self._шаг()
                continue
            ст, стб = self.строка, self.столбец
            if ch.isdigit():
                вывод.append(self._число(ст, стб))
            elif ch.isalpha() or ch == "_":
                вывод.append(self._имя(ст, стб))
            elif ch == '"':
                вывод.append(self._строка(ст, стб))
            else:
                вывод.append(self._символ(ст, стб))
        вывод.append(Токен(Вид.КОНЕЦ, "", self.строка, self.столбец))
        return вывод

    def _число(self, ст, стб):
        нач = self.i
        while self._взгляд().isdigit():
            self._шаг()
        return Токен(Вид.ЧИСЛО, self.s[нач:self.i], ст, стб)

    def _имя(self, ст, стб):
        нач = self.i
        while self._взгляд().isalnum() or self._взгляд() in ("_", "."):
            self._шаг()
        текст = self.s[нач:self.i]
        return Токен(КЛЮЧЕВЫЕ.get(текст, Вид.ИМЯ), текст, ст, стб)

    def _строка(self, ст, стб):
        self._шаг()
        нач = self.i
        while self._взгляд() != '"':
            if self.i >= len(self.s):
                raise ОшибкаЛексера(f"Незакрытая строка на {ст}:{стб}")
            self._шаг()
        текст = self.s[нач:self.i]
        self._шаг()
        return Токен(Вид.СТРОКА, текст, ст, стб)

    _ОДИНОЧНЫЕ = {
        "(": Вид.ЛСКОБ, ")": Вид.ПСКОБ, "{": Вид.ЛФИГ, "}": Вид.ПФИГ,
        "[": Вид.ЛКВАДР, "]": Вид.ПКВАДР,
        ",": Вид.ЗАПЯТАЯ, ";": Вид.ТОЧЗАП, "+": Вид.ПЛЮС, "-": Вид.МИНУС,
        "*": Вид.ЗВЕЗДА, "/": Вид.СЛЕШ, ">": Вид.БОЛЬШЕ, "<": Вид.МЕНЬШЕ,
    }

    def _символ(self, ст, стб):
        ch = self._шаг()
        if ch == "=" and self._взгляд() == "=":
            self._шаг(); return Токен(Вид.РАВНОРАВНО, "==", ст, стб)
        if ch == "=":
            return Токен(Вид.РАВНО, "=", ст, стб)
        if ch in self._ОДИНОЧНЫЕ:
            return Токен(self._ОДИНОЧНЫЕ[ch], ch, ст, стб)
        raise ОшибкаЛексера(f"Неизвестный символ '{ch}' на {ст}:{стб}")
