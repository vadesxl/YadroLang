# -*- coding: utf-8 -*-
"""AST и парсер YadroLang (recursive descent + Pratt для выражений)."""
from dataclasses import dataclass, field
from src.лексер import Вид, Токен


@dataclass
class Узел:
    строка: int = 0


@dataclass
class Число(Узел):
    значение: int = 0


@dataclass
class Строка(Узел):
    значение: str = ""


@dataclass
class Имя(Узел):
    имя: str = ""


@dataclass
class Бинарный(Узел):
    оп: str = ""; слева: Узел = None; справа: Узел = None


@dataclass
class Вызов(Узел):
    имя: str = ""; аргументы: list = field(default_factory=list)


@dataclass
class Пусть(Узел):
    имя: str = ""; значение: Узел = None


@dataclass
class Присвоить(Узел):
    имя: str = ""; значение: Узел = None


@dataclass
class Вернуть(Узел):
    значение: Узел = None


@dataclass
class Если(Узел):
    условие: Узел = None
    тогда: list = field(default_factory=list)
    иначе: list = field(default_factory=list)


@dataclass
class Пока(Узел):
    условие: Узел = None
    тело: list = field(default_factory=list)


@dataclass
class Функция(Узел):
    имя: str = ""
    параметры: list = field(default_factory=list)
    тело: list = field(default_factory=list)
    мандаты: list = field(default_factory=list)


@dataclass
class Программа(Узел):
    функции: list = field(default_factory=list)


class ОшибкаПарсера(Exception):
    ...


ПРИОРИТЕТ = {
    Вид.РАВНОРАВНО: 1, Вид.БОЛЬШЕ: 1, Вид.МЕНЬШЕ: 1,
    Вид.ПЛЮС: 2, Вид.МИНУС: 2,
    Вид.ЗВЕЗДА: 3, Вид.СЛЕШ: 3,
}
ОП_ТЕКСТ = {Вид.ПЛЮС: "+", Вид.МИНУС: "-", Вид.ЗВЕЗДА: "*", Вид.СЛЕШ: "/",
            Вид.БОЛЬШЕ: ">", Вид.МЕНЬШЕ: "<", Вид.РАВНОРАВНО: "=="}


class Парсер:
    def __init__(self, токены):
        self.т = токены; self.i = 0

    def _тек(self):
        return self.т[self.i]

    def _съесть(self, вид=None):
        ток = self.т[self.i]
        if вид and ток.вид != вид:
            raise ОшибкаПарсера(f"Ожидался {вид}, получен '{ток.текст}' на {ток.строка}")
        self.i += 1
        return ток

    def разобрать(self):
        прог = Программа()
        while self._тек().вид != Вид.КОНЕЦ:
            прог.функции.append(self._функция())
        return прог

    def _функция(self):
        ст = self._съесть(Вид.ФУНК).строка
        имя = self._съесть(Вид.ИМЯ).текст
        self._съесть(Вид.ЛСКОБ)
        параметры = []
        while self._тек().вид != Вид.ПСКОБ:
            параметры.append(self._съесть(Вид.ИМЯ).текст)
            if self._тек().вид == Вид.ЗАПЯТАЯ:
                self._съесть()
        self._съесть(Вид.ПСКОБ)
        мандаты = []
        if self._тек().вид == Вид.ИМЯ and self._тек().текст == "требует":
            self._съесть()
            self._съесть(Вид.ЛКВАДР)
            while self._тек().вид != Вид.ПКВАДР:
                мандаты.append(self._съесть(Вид.ИМЯ).текст)
                if self._тек().вид == Вид.ЗАПЯТАЯ:
                    self._съесть()
            self._съесть(Вид.ПКВАДР)
        тело = self._блок()
        return Функция(ст, имя, параметры, тело, мандаты)

    def _блок(self):
        self._съесть(Вид.ЛФИГ)
        утв = []
        while self._тек().вид != Вид.ПФИГ:
            утв.append(self._утверждение())
        self._съесть(Вид.ПФИГ)
        return утв

    def _утверждение(self):
        в = self._тек().вид
        if в == Вид.ВЕРНУТЬ:
            ст = self._съесть().строка
            return Вернуть(ст, self._выражение())
        if в == Вид.ПУСТЬ:
            ст = self._съесть().строка
            имя = self._съесть(Вид.ИМЯ).текст
            self._съесть(Вид.РАВНО)
            return Пусть(ст, имя, self._выражение())
        if в == Вид.ЕСЛИ:
            return self._если()
        if в == Вид.ПОКА:
            ст = self._съесть().строка
            усл = self._выражение()
            return Пока(ст, усл, self._блок())
        if в == Вид.ИМЯ and self.т[self.i + 1].вид == Вид.РАВНО:
            ст = self._тек().строка
            имя = self._съесть().текст
            self._съесть(Вид.РАВНО)
            return Присвоить(ст, имя, self._выражение())
        return self._выражение()

    def _если(self):
        ст = self._съесть(Вид.ЕСЛИ).строка
        усл = self._выражение()
        тогда = self._блок()
        иначе = []
        if self._тек().вид == Вид.ИНАЧЕ:
            self._съесть()
            иначе = self._блок()
        return Если(ст, усл, тогда, иначе)

    def _выражение(self, мин=0):
        слева = self._первичное()
        while True:
            в = self._тек().вид
            пр = ПРИОРИТЕТ.get(в)
            if пр is None or пр < мин:
                break
            оп = self._съесть()
            справа = self._выражение(пр + 1)
            слева = Бинарный(оп.строка, ОП_ТЕКСТ[в], слева, справа)
        return слева

    def _первичное(self):
        ток = self._тек()
        if ток.вид == Вид.ЧИСЛО:
            self._съесть(); return Число(ток.строка, int(ток.текст))
        if ток.вид == Вид.СТРОКА:
            self._съесть(); return Строка(ток.строка, ток.текст)
        if ток.вид == Вид.ЛСКОБ:
            self._съесть(); вн = self._выражение(); self._съесть(Вид.ПСКОБ); return вн
        if ток.вид == Вид.ИМЯ:
            self._съесть()
            if self._тек().вид == Вид.ЛСКОБ:
                self._съесть()
                арг = []
                while self._тек().вид != Вид.ПСКОБ:
                    арг.append(self._выражение())
                    if self._тек().вид == Вид.ЗАПЯТАЯ:
                        self._съесть()
                self._съесть(Вид.ПСКОБ)
                return Вызов(ток.строка, ток.текст, арг)
            return Имя(ток.строка, ток.текст)
        raise ОшибкаПарсера(f"Неожиданный токен '{ток.текст}' на {ток.строка}")
