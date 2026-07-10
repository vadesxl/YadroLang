# -*- coding: utf-8 -*-
import hashlib
from llvmlite import ir,binding as llvm
from src.синтаксис import Вернуть,Пусть,Присвоить,Если,Пока,Число,Строка,Булево,Имя,Бинарный,Вызов
I64,BOOL,BYTE,I32=ir.IntType(64),ir.IntType(1),ir.IntType(8),ir.IntType(32);PTR=BYTE.as_pointer()
class ОшибкаКодогена(Exception):pass
def тип(т):return {"i64":I64,"bool":BOOL,"string":PTR}[т]
def символ(префикс,имя):return f"yadro.{префикс}.{hashlib.sha256(имя.encode()).hexdigest()[:16]}"
class Кодоген:
 def __init__(self):self.модуль=ir.Module(name="ядро");self.модуль.triple=llvm.get_default_triple();self.ф={};self.ext={};self.скоуп={};self.b=None;self.n=0;self.printf=ir.Function(self.модуль,ir.FunctionType(I32,[PTR],var_arg=True),name="printf")
 def сгенерировать(self,прог):
  self.fi=self._глоб("%lld\n");self.fs=self._глоб("%s\n");self.fr=self._глоб("Результат старт(): %lld\n")
  for ф in прог.функции:self.ф[ф.имя]=ir.Function(self.модуль,ir.FunctionType(тип(ф.выведенный_тип_возврата),[тип(x) for x in ф.выведенные_типы_параметров]),name=символ("fn",ф.имя))
  for ф in прог.функции:self._функция(ф)
  self._entry();т=str(self.модуль)
  try:м=llvm.parse_assembly(т);м.verify()
  except Exception as e:raise ОшибкаКодогена(f"LLVM verification failed: {e}") from e
  return т
 def _entry(self):
  if "старт" not in self.ф:return
  fn=ir.Function(self.модуль,ir.FunctionType(I32,[]),name="main");b=ir.IRBuilder(fn.append_basic_block("entry"));р=b.call(self.ф["старт"],[])
  if р.type==BOOL:р=b.zext(р,I64)
  if р.type==I64:b.call(self.printf,[self._ptr(b,self.fr),р])
  b.ret(I32(0))
 def _функция(self,ast):
  fn=self.ф[ast.имя];self.b=ir.IRBuilder(fn.append_basic_block("entry"));self.скоуп={}
  for arg,name,т in zip(fn.args,ast.параметры,ast.выведенные_типы_параметров):яч=self.b.alloca(тип(т),name=f"var.{name}");self.b.store(arg,яч);self.скоуп[name]=яч
  self._тело(ast.тело)
  if not self.b.block.is_terminated:self.b.ret({"i64":I64(0),"bool":BOOL(0),"string":ir.Constant(PTR,None)}[ast.выведенный_тип_возврата])
 def _тело(self,тело):
  for у in тело:
   if self.b.block.is_terminated:break
   self._утв(у)
 def _утв(self,у):
  if isinstance(у,Вернуть):self.b.ret(self._выр(у.значение))
  elif isinstance(у,Пусть):v=self._выр(у.значение);яч=self.b.alloca(v.type,name=f"var.{у.имя}");self.b.store(v,яч);self.скоуп[у.имя]=яч
  elif isinstance(у,Присвоить):self.b.store(self._выр(у.значение),self.скоуп[у.имя])
  elif isinstance(у,Если):self._если(у)
  elif isinstance(у,Пока):self._пока(у)
  else:self._выр(у)
 def _если(self,у):
  c=self._bool(self._выр(у.условие));fn=self.b.function;т=fn.append_basic_block("if.then");и=fn.append_basic_block("if.else") if у.иначе else None;к=fn.append_basic_block("if.end");self.b.cbranch(c,т,и or к);self.b.position_at_end(т);self._тело(у.тогда)
  if not self.b.block.is_terminated:self.b.branch(к)
  if и:
   self.b.position_at_end(и);self._тело(у.иначе)
   if not self.b.block.is_terminated:self.b.branch(к)
  self.b.position_at_end(к)
 def _пока(self,у):
  fn=self.b.function;c=fn.append_basic_block("while.cond");т=fn.append_basic_block("while.body");к=fn.append_basic_block("while.end");self.b.branch(c);self.b.position_at_end(c);self.b.cbranch(self._bool(self._выр(у.условие)),т,к);self.b.position_at_end(т);self._тело(у.тело)
  if not self.b.block.is_terminated:self.b.branch(c)
  self.b.position_at_end(к)
 def _выр(self,у):
  if isinstance(у,Число):return I64(у.значение)
  if isinstance(у,Булево):return BOOL(1 if у.значение else 0)
  if isinstance(у,Строка):return self._ptr(self.b,self._глоб(у.значение))
  if isinstance(у,Имя):return self.b.load(self.скоуп[у.имя])
  if isinstance(у,Бинарный):
   л,п=self._выр(у.слева),self._выр(у.справа);ops={"+":self.b.add,"-":self.b.sub,"*":self.b.mul,"/":self.b.sdiv};return ops[у.оп](л,п) if у.оп in ops else self.b.icmp_signed(у.оп,л,п)
  if isinstance(у,Вызов):
   if у.имя=="печать":
    v=self._выр(у.аргументы[0])
    if v.type==PTR:self.b.call(self.printf,[self._ptr(self.b,self.fs),v])
    else:
     if v.type==BOOL:v=self.b.zext(v,I64)
     self.b.call(self.printf,[self._ptr(self.b,self.fi),v])
    return I64(0)
   а=[self._выр(x) for x in у.аргументы]
   if у.имя in self.ф:return self.b.call(self.ф[у.имя],а)
   sig=tuple(x.type for x in а);prev=self.ext.get(у.имя)
   if prev and prev[0]!=sig:raise ОшибкаКодогена(f"extern ABI mismatch '{у.имя}'")
   if not prev:self.ext[у.имя]=(sig,ir.Function(self.модуль,ir.FunctionType(I64,list(sig)),name=символ("abi.v1",у.имя)))
   return self.b.call(self.ext[у.имя][1],а)
  raise ОшибкаКодогена(f"неподдерживаемый узел {type(у).__name__}")
 def _глоб(self,т):
  d=bytearray(т.encode()+b"\0");a=ir.ArrayType(BYTE,len(d));g=ir.GlobalVariable(self.модуль,a,name=f".str.{self.n}");self.n+=1;g.linkage="internal";g.global_constant=True;g.initializer=ir.Constant(a,d);return g
 @staticmethod
 def _ptr(b,g):return b.gep(g,[I32(0),I32(0)],inbounds=True)
 def _bool(self,v):return v if v.type==BOOL else self.b.icmp_signed("!=",v,I64(0))
