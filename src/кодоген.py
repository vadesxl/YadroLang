# -*- coding: utf-8 -*-
"""Проверяемый LLVM IR генератор, ABI v1."""
import hashlib,re
from llvmlite import ir,binding as llvm
from src.синтаксис import Программа,Функция,Вернуть,Пусть,Присвоить,Если,Пока,Число,Булево,Строка,Имя,Бинарный,Вызов
ЦЕЛОЕ=ir.IntType(64);БУЛЕВ=ir.IntType(1);БАЙТ=ir.IntType(8);УКАЗ=БАЙТ.as_pointer();I32=ir.IntType(32)
class ОшибкаКодогена(Exception):pass
def _символ(префикс,имя):
 читаемое=re.sub(r"[^A-Za-z0-9_]","_",имя)[:40];хэш=hashlib.sha256(имя.encode()).hexdigest()[:12];return f"yadro_{префикс}_v1_{читаемое}_{хэш}"
class Кодоген:
 def __init__(self):
  self.модуль=ir.Module(name="ядро");self.модуль.triple=llvm.get_default_triple();self.функции={};self.строитель=None;self.скоуп={};self.внешние={};self._счёт=0;self.printf=ir.Function(self.модуль,ir.FunctionType(I32,[УКАЗ],var_arg=True),name="printf")
 def _внешняя(self,имя,арность):
  if имя in self.внешние:
   функция,известно=self.внешние[имя]
   if известно!=арность:raise ОшибкаКодогена(f"Несовместимый extern ABI '{имя}': {известно} и {арность}")
   return функция
  функция=ir.Function(self.модуль,ir.FunctionType(ЦЕЛОЕ,[ЦЕЛОЕ]*арность),name=_символ("ext",имя));self.внешние[имя]=(функция,арность);return функция
 def _строка(self,текст):
  данные=bytearray(текст.encode()+b"\0");тип=ir.ArrayType(БАЙТ,len(данные));значение=ir.GlobalVariable(self.модуль,тип,name=f".str.{self._счёт}");self._счёт+=1;значение.linkage="internal";значение.global_constant=True;значение.initializer=ir.Constant(тип,данные);return значение
 def _указ(self,b,значение):ноль=ir.Constant(I32,0);return b.gep(значение,[ноль,ноль],inbounds=True)
 def _ц64(self,значение):return self.строитель.zext(значение,ЦЕЛОЕ) if значение.type==БУЛЕВ else значение
 def сгенерировать(self,программа):
  self._фмт_число=self._строка("%lld\n");self._фмт_рез=self._строка("Результат старт(): %lld\n");self._фмт_строка=self._строка("%s\n")
  for ф in программа.функции:self.функции[ф.имя]=ir.Function(self.модуль,ir.FunctionType(ЦЕЛОЕ,[ЦЕЛОЕ]*len(ф.параметры)),name=_символ("entry" if ф.имя=="старт" else "fn",ф.имя))
  for ф in программа.функции:self._функция(ф)
  self._главная();текст=str(self.модуль)
  try:модуль=llvm.parse_assembly(текст);модуль.verify()
  except Exception as ошибка:raise ОшибкаКодогена(f"LLVM verification failed: {ошибка}") from ошибка
  return текст
 def _главная(self):
  функция=ir.Function(self.модуль,ir.FunctionType(I32,[]),name="main");b=ir.IRBuilder(функция.append_basic_block("entry"));рез=b.call(self.функции["старт"],[]);b.call(self.printf,[self._указ(b,self._фмт_рез),рез]);b.ret(I32(0))
 def _функция(self,узел):
  функция=self.функции[узел.имя];self.строитель=ir.IRBuilder(функция.append_basic_block("entry"));self.скоуп={}
  for аргумент,имя in zip(функция.args,узел.параметры):ячейка=self.строитель.alloca(ЦЕЛОЕ,name=имя);self.строитель.store(аргумент,ячейка);self.скоуп[имя]=ячейка
  self._тело(узел.тело)
  if not self.строитель.block.is_terminated:self.строитель.ret(ЦЕЛОЕ(0))
 def _тело(self,тело):
  for у in тело:
   if self.строитель.block.is_terminated:break
   self._утверждение(у)
 def _утверждение(self,у):
  if isinstance(у,Вернуть):self.строитель.ret(self._ц64(self._выражение(у.значение)))
  elif isinstance(у,Пусть):ячейка=self.строитель.alloca(ЦЕЛОЕ,name=у.имя);self.строитель.store(self._ц64(self._выражение(у.значение)),ячейка);self.скоуп[у.имя]=ячейка
  elif isinstance(у,Присвоить):self.строитель.store(self._ц64(self._выражение(у.значение)),self.скоуп[у.имя])
  elif isinstance(у,Если):self._если(у)
  elif isinstance(у,Пока):self._пока(у)
  else:self._выражение(у)
 def _если(self,у):
  условие=self._булев(self._выражение(у.условие));ф=self.строитель.function;тогда=ф.append_basic_block("if.then");иначе=ф.append_basic_block("if.else") if у.иначе else None;конец=ф.append_basic_block("if.end");self.строитель.cbranch(условие,тогда,иначе or конец);self.строитель.position_at_end(тогда);self._тело(у.тогда)
  if not self.строитель.block.is_terminated:self.строитель.branch(конец)
  if иначе:
   self.строитель.position_at_end(иначе);self._тело(у.иначе)
   if not self.строитель.block.is_terminated:self.строитель.branch(конец)
  self.строитель.position_at_end(конец)
 def _пока(self,у):
  ф=self.строитель.function;условие=ф.append_basic_block("loop.cond");тело=ф.append_basic_block("loop.body");выход=ф.append_basic_block("loop.exit");self.строитель.branch(условие);self.строитель.position_at_end(условие);self.строитель.cbranch(self._булев(self._выражение(у.условие)),тело,выход);self.строитель.position_at_end(тело);self._тело(у.тело)
  if not self.строитель.block.is_terminated:self.строитель.branch(условие)
  self.строитель.position_at_end(выход)
 def _выражение(self,у):
  if isinstance(у,Число):return ЦЕЛОЕ(у.значение)
  if isinstance(у,Булево):return БУЛЕВ(1 if у.значение else 0)
  if isinstance(у,Строка):raise ОшибкаКодогена("Строка допустима только как литерал печать")
  if isinstance(у,Имя):return self.строитель.load(self.скоуп[у.имя],name=у.имя)
  if isinstance(у,Бинарный):
   л=self._ц64(self._выражение(у.слева));п=self._ц64(self._выражение(у.справа));операции={"+":self.строитель.add,"-":self.строитель.sub,"*":self.строитель.mul,"/":self.строитель.sdiv}
   return операции[у.оп](л,п) if у.оп in операции else self.строитель.icmp_signed(у.оп,л,п)
  if isinstance(у,Вызов):
   if у.имя=="печать":
    значение=у.аргументы[0]
    if isinstance(значение,Строка):текст=self._строка(значение.значение);self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_строка),self._указ(self.строитель,текст)])
    else:self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_число),self._ц64(self._выражение(значение))])
    return ЦЕЛОЕ(0)
   аргументы=[self._ц64(self._выражение(а)) for а in у.аргументы];цель=self.функции.get(у.имя) or self._внешняя(у.имя,len(аргументы));return self.строитель.call(цель,аргументы)
  raise ОшибкаКодогена(f"Неизвестный AST {type(у).__name__}")
 def _булев(self,значение):return значение if значение.type==БУЛЕВ else self.строитель.icmp_signed("!=",значение,ЦЕЛОЕ(0))
