# -*- coding: utf-8 -*-
"""Проверяемый генератор LLVM IR для ABI YadroLang v1."""
from llvmlite import ir,binding as llvm
from src.синтаксис import (Программа,Вернуть,Пусть,Присвоить,Если,Пока,Число,Строка,Имя,Бинарный,Вызов)
ЦЕЛОЕ=ir.IntType(64);БУЛЕВ=ir.IntType(1);БАЙТ=ir.IntType(8);УКАЗ=БАЙТ.as_pointer();I32=ir.IntType(32)
class ОшибкаКодогена(Exception):pass
class Кодоген:
 def __init__(self):
  self.модуль=ir.Module(name="ядро");self.модуль.triple=llvm.get_default_triple();self.функции={};self.строитель=None;self.скоуп={};self._счёт=0;self.внешние={};self.printf=ir.Function(self.модуль,ir.FunctionType(I32,[УКАЗ],var_arg=True),name="printf")
 def _символ_api(self,имя):return "yadro_ext_v1_"+имя.replace(".","_")
 def _внешняя(self,имя,арность):
  символ=self._символ_api(имя);сигнатура=ir.FunctionType(ЦЕЛОЕ,[ЦЕЛОЕ]*арность);существует=self.внешние.get(символ)
  if существует and str(существует.function_type)!=str(сигнатура):raise ОшибкаКодогена(f"несовместимый extern ABI '{имя}'")
  if not существует:существует=ir.Function(self.модуль,сигнатура,name=символ);self.внешние[символ]=существует
  return существует
 def _строка(self,текст):
  данные=bytearray(текст.encode("utf-8")+b"\0");тип=ir.ArrayType(БАЙТ,len(данные));г=ir.GlobalVariable(self.модуль,тип,name=f".str.{self._счёт}");self._счёт+=1;г.linkage="internal";г.global_constant=True;г.initializer=ir.Constant(тип,данные);return г
 def _указ(self,b,г):ноль=I32(0);return b.gep(г,[ноль,ноль],inbounds=True)
 def _i64(self,значение):return self.строитель.zext(значение,ЦЕЛОЕ) if значение.type==БУЛЕВ else значение
 def сгенерировать(self,программа:Программа):
  self._фмт_число=self._строка("%lld\n");self._фмт_рез=self._строка("Результат старт(): %lld\n");self._фмт_строка=self._строка("%s\n")
  for ф in программа.функции:self.функции[ф.имя]=ir.Function(self.модуль,ir.FunctionType(ЦЕЛОЕ,[ЦЕЛОЕ]*len(ф.параметры)),name="yadro_fn_"+ф.имя)
  for ф in программа.функции:self._функция(ф)
  self._главная();текст=str(self.модуль)
  try:модуль=llvm.parse_assembly(текст);модуль.verify()
  except Exception as ошибка:raise ОшибкаКодогена(f"LLVM verification failed: {ошибка}") from ошибка
  return текст
 def _главная(self):
  fn=ir.Function(self.модуль,ir.FunctionType(I32,[]),name="main");b=ir.IRBuilder(fn.append_basic_block("entry"));рез=b.call(self.функции["старт"],[]);b.call(self.printf,[self._указ(b,self._фмт_рез),рез]);b.ret(I32(0))
 def _функция(self,ф):
  self.строитель=ir.IRBuilder(self.функции[ф.имя].append_basic_block("entry"));self.скоуп={}
  for арг,имя in zip(self.функции[ф.имя].args,ф.параметры):яч=self.строитель.alloca(ЦЕЛОЕ,name=имя);self.строитель.store(арг,яч);self.скоуп[имя]=яч
  for утверждение in ф.тело:
   if self.строитель.block.is_terminated:break
   self._утверждение(утверждение)
  if not self.строитель.block.is_terminated:self.строитель.ret(ЦЕЛОЕ(0))
 def _утверждение(self,у):
  if isinstance(у,Вернуть):self.строитель.ret(self._i64(self._выражение(у.значение)))
  elif isinstance(у,Пусть):яч=self.строитель.alloca(ЦЕЛОЕ,name=у.имя);self.строитель.store(self._i64(self._выражение(у.значение)),яч);self.скоуп[у.имя]=яч
  elif isinstance(у,Присвоить):self.строитель.store(self._i64(self._выражение(у.значение)),self.скоуп[у.имя])
  elif isinstance(у,Если):self._если(у)
  elif isinstance(у,Пока):self._пока(у)
  else:self._выражение(у)
 def _если(self,у):
  fn=self.строитель.function;тогда=fn.append_basic_block("then");иначе=fn.append_basic_block("else") if у.иначе else None;конец=fn.append_basic_block("if.end");self.строитель.cbranch(self._булев(self._выражение(у.условие)),тогда,иначе or конец);self.строитель.position_at_end(тогда)
  for s in у.тогда:
   if self.строитель.block.is_terminated:break
   self._утверждение(s)
  if not self.строитель.block.is_terminated:self.строитель.branch(конец)
  if иначе:
   self.строитель.position_at_end(иначе)
   for s in у.иначе:
    if self.строитель.block.is_terminated:break
    self._утверждение(s)
   if not self.строитель.block.is_terminated:self.строитель.branch(конец)
  self.строитель.position_at_end(конец)
 def _пока(self,у):
  fn=self.строитель.function;условие=fn.append_basic_block("loop.cond");тело=fn.append_basic_block("loop.body");конец=fn.append_basic_block("loop.end");self.строитель.branch(условие);self.строитель.position_at_end(условие);self.строитель.cbranch(self._булев(self._выражение(у.условие)),тело,конец);self.строитель.position_at_end(тело)
  for s in у.тело:
   if self.строитель.block.is_terminated:break
   self._утверждение(s)
  if not self.строитель.block.is_terminated:self.строитель.branch(условие)
  self.строитель.position_at_end(конец)
 def _выражение(self,в):
  if isinstance(в,Число):return ЦЕЛОЕ(в.значение)
  if isinstance(в,Имя):return self.строитель.load(self.скоуп[в.имя],name=в.имя)
  if isinstance(в,Бинарный):
   л=self._выражение(в.слева);п=self._выражение(в.справа);return {"+":lambda:self.строитель.add(л,п),"-":lambda:self.строитель.sub(л,п),"*":lambda:self.строитель.mul(л,п),"/":lambda:self.строитель.sdiv(л,п),">":lambda:self.строитель.icmp_signed(">",л,п),"<":lambda:self.строитель.icmp_signed("<",л,п),"==":lambda:self.строитель.icmp_signed("==",л,п)}[в.оп]()
  if isinstance(в,Вызов):
   if в.имя=="печать":
    узел=в.аргументы[0]
    if isinstance(узел,Строка):г=self._строка(узел.значение);self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_строка),self._указ(self.строитель,г)])
    else:self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_число),self._i64(self._выражение(узел))])
    return ЦЕЛОЕ(0)
   аргументы=[self._i64(self._выражение(а)) for а in в.аргументы];return self.строитель.call(self.функции[в.имя],аргументы) if в.имя in self.функции else self.строитель.call(self._внешняя(в.имя,len(аргументы)),аргументы)
  raise ОшибкаКодогена(f"невозможно понизить {type(в).__name__}")
 def _булев(self,значение):return значение if значение.type==БУЛЕВ else self.строитель.icmp_signed("!=",значение,ЦЕЛОЕ(0))
