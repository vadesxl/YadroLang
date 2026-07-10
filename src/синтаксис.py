# -*- coding: utf-8 -*-
"""AST и bounded Pratt-парсер YadroLang."""
from dataclasses import dataclass,field
from src.лексер import Вид
@dataclass
class Узел:строка:int=0
@dataclass
class Число(Узел):значение:int=0
@dataclass
class Строка(Узел):значение:str=""
@dataclass
class Булево(Узел):значение:bool=False
@dataclass
class Имя(Узел):имя:str=""
@dataclass
class Бинарный(Узел):оп:str="";слева:Узел=None;справа:Узел=None
@dataclass
class Вызов(Узел):имя:str="";аргументы:list=field(default_factory=list)
@dataclass
class Пусть(Узел):имя:str="";значение:Узел=None
@dataclass
class Присвоить(Узел):имя:str="";значение:Узел=None
@dataclass
class Вернуть(Узел):значение:Узел=None
@dataclass
class Если(Узел):условие:Узел=None;тогда:list=field(default_factory=list);иначе:list=field(default_factory=list)
@dataclass
class Пока(Узел):условие:Узел=None;тело:list=field(default_factory=list)
@dataclass
class Функция(Узел):имя:str="";параметры:list=field(default_factory=list);тело:list=field(default_factory=list);мандаты:list=field(default_factory=list)
@dataclass
class Программа(Узел):функции:list=field(default_factory=list)
class ОшибкаПарсера(Exception):pass
ПРИОРИТЕТ={Вид.РАВНОРАВНО:1,Вид.БОЛЬШЕ:1,Вид.МЕНЬШЕ:1,Вид.ПЛЮС:2,Вид.МИНУС:2,Вид.ЗВЕЗДА:3,Вид.СЛЕШ:3};ОП={Вид.ПЛЮС:"+",Вид.МИНУС:"-",Вид.ЗВЕЗДА:"*",Вид.СЛЕШ:"/",Вид.БОЛЬШЕ:">",Вид.МЕНЬШЕ:"<",Вид.РАВНОРАВНО:"=="}
class Парсер:
 МАКС=512
 def __init__(self,т):self.т=т;self.i=0;self.глубина=0
 def _тек(self):return self.т[self.i]
 def _съесть(self,вид=None):
  ток=self.т[self.i]
  if вид and ток.вид!=вид:raise ОшибкаПарсера(f"Ожидался {вид}, получен '{ток.текст}' на {ток.строка}")
  self.i+=1;return ток
 def разобрать(self):
  п=Программа()
  while self._тек().вид!=Вид.КОНЕЦ:
   до=self.i;п.функции.append(self._функция())
   if self.i<=до:raise ОшибкаПарсера("парсер не продвинулся")
  return п
 def _функция(self):
  ст=self._съесть(Вид.ФУНК).строка;имя=self._съесть(Вид.ИМЯ).текст;self._съесть(Вид.ЛСКОБ);п=[]
  while self._тек().вид!=Вид.ПСКОБ:
   п.append(self._съесть(Вид.ИМЯ).текст)
   if self._тек().вид==Вид.ЗАПЯТАЯ:self._съесть()
  self._съесть(Вид.ПСКОБ);м=[]
  if self._тек().вид==Вид.ИМЯ and self._тек().текст=="требует":
   self._съесть();self._съесть(Вид.ЛКВАДР)
   while self._тек().вид!=Вид.ПКВАДР:
    м.append(self._съесть(Вид.ИМЯ).текст)
    if self._тек().вид==Вид.ЗАПЯТАЯ:self._съесть()
   self._съесть(Вид.ПКВАДР)
  return Функция(ст,имя,п,self._блок(),м)
 def _блок(self):
  self._съесть(Вид.ЛФИГ);т=[]
  while self._тек().вид!=Вид.ПФИГ:
   if self._тек().вид==Вид.КОНЕЦ:raise ОшибкаПарсера("незакрытый блок")
   до=self.i;т.append(self._утв())
   if self.i<=до:raise ОшибкаПарсера("парсер не продвинулся")
  self._съесть(Вид.ПФИГ);return т
 def _утв(self):
  в=self._тек().вид
  if в==Вид.ВЕРНУТЬ:ст=self._съесть().строка;return Вернуть(ст,self._выр())
  if в==Вид.ПУСТЬ:ст=self._съесть().строка;имя=self._съесть(Вид.ИМЯ).текст;self._съесть(Вид.РАВНО);return Пусть(ст,имя,self._выр())
  if в==Вид.ЕСЛИ:return self._если()
  if в==Вид.ПОКА:ст=self._съесть().строка;условие=self._выр();return Пока(ст,условие,self._блок())
  if в==Вид.ИМЯ and self.i+1<len(self.т) and self.т[self.i+1].вид==Вид.РАВНО:ст=self._тек().строка;имя=self._съесть().текст;self._съесть();return Присвоить(ст,имя,self._выр())
  return self._выр()
 def _если(self):
  ст=self._съесть(Вид.ЕСЛИ).строка;условие=self._выр();тогда=self._блок();иначе=[]
  if self._тек().вид==Вид.ИНАЧЕ:self._съесть();иначе=self._блок()
  return Если(ст,условие,тогда,иначе)
 def _выр(self,мин=0):
  self.глубина+=1
  if self.глубина>self.МАКС:raise ОшибкаПарсера("превышен предел вложенности")
  try:
   слева=self._первичное()
   while True:
    в=self._тек().вид;пр=ПРИОРИТЕТ.get(в)
    if пр is None or пр<мин:break
    оп=self._съесть();слева=Бинарный(оп.строка,ОП[в],слева,self._выр(пр+1))
   return слева
  finally:self.глубина-=1
 def _первичное(self):
  ток=self._тек()
  if ток.вид==Вид.ЧИСЛО:self._съесть();return Число(ток.строка,int(ток.текст))
  if ток.вид==Вид.СТРОКА:self._съесть();return Строка(ток.строка,ток.текст)
  if ток.вид in (Вид.ИСТИНА,Вид.ЛОЖЬ):self._съесть();return Булево(ток.строка,ток.вид==Вид.ИСТИНА)
  if ток.вид==Вид.ЛСКОБ:self._съесть();в=self._выр();self._съесть(Вид.ПСКОБ);return в
  if ток.вид==Вид.ИМЯ:
   self._съесть()
   if self._тек().вид==Вид.ЛСКОБ:
    self._съесть();а=[]
    while self._тек().вид!=Вид.ПСКОБ:
     а.append(self._выр())
     if self._тек().вид==Вид.ЗАПЯТАЯ:self._съесть()
    self._съесть(Вид.ПСКОБ);return Вызов(ток.строка,ток.текст,а)
   return Имя(ток.строка,ток.текст)
  raise ОшибкаПарсера(f"Неожиданный токен '{ток.текст}' на {ток.строка}")
