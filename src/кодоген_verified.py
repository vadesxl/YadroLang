# -*- coding: utf-8 -*-
"""Verified LLVM IR backend с типизированной памятью и ABI v1."""
import hashlib
from llvmlite import ir,binding as llvm
from src.синтаксис import Вернуть,Пусть,Присвоить,Если,Пока,Число,Строка,Булево,Имя,Бинарный,Вызов
ЦЕЛОЕ,БУЛЕВ,БАЙТ,I32=ir.IntType(64),ir.IntType(1),ir.IntType(8),ir.IntType(32);УКАЗ=БАЙТ.as_pointer()
class ОшибкаКодогена(Exception):pass
def тип(n):return {"i64":ЦЕЛОЕ,"bool":БУЛЕВ,"string":УКАЗ}[n]
def символ(prefix,name):return f"yadro.{prefix}.{hashlib.sha256(name.encode()).hexdigest()[:16]}"
class Кодоген:
 def __init__(self):
  self.модуль=ir.Module(name="ядро");self.модуль.triple=llvm.get_default_triple();self.функции={};self.внешние={};self.скоуп={};self.строитель=None;self._счёт=0;self.printf=ir.Function(self.модуль,ir.FunctionType(I32,[УКАЗ],var_arg=True),name="printf")
 def сгенерировать(self,прог):
  self._фмт_i64=self._глоб("%lld\n");self._фмт_s=self._глоб("%s\n");self._фмт_r=self._глоб("Результат старт(): %lld\n")
  for ф in прог.функции:self.функции[ф.имя]=ir.Function(self.модуль,ir.FunctionType(тип(ф.выведенный_тип_возврата),[тип(x) for x in ф.выведенные_типы_параметров]),name=символ("fn",ф.имя))
  for ф in прог.функции:self._функция(ф)
  self._главная();текст=str(self.модуль)
  try:м=llvm.parse_assembly(текст);м.verify()
  except Exception as e:raise ОшибкаКодогена(f"LLVM verification failed: {e}") from e
  return текст
 def _главная(self):
  if "старт" not in self.функции:return
  fn=ir.Function(self.модуль,ir.FunctionType(I32,[]),name="main");b=ir.IRBuilder(fn.append_basic_block("entry"));r=b.call(self.функции["старт"],[])
  if r.type==БУЛЕВ:r=b.zext(r,ЦЕЛОЕ)
  if r.type==ЦЕЛОЕ:b.call(self.printf,[self._указ(b,self._фмт_r),r])
  b.ret(I32(0))
 def _функция(self,ast):
  fn=self.функции[ast.имя];self.строитель=ir.IRBuilder(fn.append_basic_block("entry"));self.скоуп={}
  for arg,name,t in zip(fn.args,ast.параметры,ast.выведенные_типы_параметров):cell=self.строитель.alloca(тип(t),name=f"var.{name}");self.строитель.store(arg,cell);self.скоуп[name]=(cell,t)
  self._тело(ast.тело)
  if not self.строитель.block.is_terminated:self.строитель.ret({"i64":ЦЕЛОЕ(0),"bool":БУЛЕВ(0),"string":ir.Constant(УКАЗ,None)}[ast.выведенный_тип_возврата])
 def _тело(self,тело):
  for у in тело:
   if self.строитель.block.is_terminated:break
   self._утв(у)
 def _утв(self,у):
  if isinstance(у,Вернуть):self.строитель.ret(self._выр(у.значение))
  elif isinstance(у,Пусть):v=self._выр(у.значение);cell=self.строитель.alloca(v.type,name=f"var.{у.имя}");self.строитель.store(v,cell);self.скоуп[у.имя]=(cell,у.выведенный_тип)
  elif isinstance(у,Присвоить):self.строитель.store(self._выр(у.значение),self.скоуп[у.имя][0])
  elif isinstance(у,Если):self._если(у)
  elif isinstance(у,Пока):self._пока(у)
  else:self._выр(у)
 def _если(self,у):
  c=self._бул(self._выр(у.условие));fn=self.строитель.function;т=fn.append_basic_block("if.then");и=fn.append_basic_block("if.else") if у.иначе else None;к=fn.append_basic_block("if.end");self.строитель.cbranch(c,т,и or к);self.строитель.position_at_end(т);self._тело(у.тогда)
  if not self.строитель.block.is_terminated:self.строитель.branch(к)
  if и:
   self.строитель.position_at_end(и);self._тело(у.иначе)
   if not self.строитель.block.is_terminated:self.строитель.branch(к)
  self.строитель.position_at_end(к)
 def _пока(self,у):
  fn=self.строитель.function;c=fn.append_basic_block("while.cond");т=fn.append_basic_block("while.body");к=fn.append_basic_block("while.end");self.строитель.branch(c);self.строитель.position_at_end(c);self.строитель.cbranch(self._бул(self._выр(у.условие)),т,к);self.строитель.position_at_end(т);self._тело(у.тело)
  if not self.строитель.block.is_terminated:self.строитель.branch(c)
  self.строитель.position_at_end(к)
 def _выр(self,в):
  if isinstance(в,Число):return ЦЕЛОЕ(в.значение)
  if isinstance(в,Булево):return БУЛЕВ(1 if в.значение else 0)
  if isinstance(в,Строка):return self._указ(self.строитель,self._глоб(в.значение))
  if isinstance(в,Имя):return self.строитель.load(self.скоуп[в.имя][0],name=f"load.{в.имя}")
  if isinstance(в,Бинарный):
   л,п=self._выр(в.слева),self._выр(в.справа);ops={"+":self.строитель.add,"-":self.строитель.sub,"*":self.строитель.mul,"/":self.строитель.sdiv}
   return ops[в.оп](л,п) if в.оп in ops else self.строитель.icmp_signed(в.оп,л,п)
  if isinstance(в,Вызов):
   if в.имя=="печать":
    val=self._выр(в.аргументы[0])
    if val.type==УКАЗ:self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_s),val])
    else:
     if val.type==БУЛЕВ:val=self.строитель.zext(val,ЦЕЛОЕ)
     self.строитель.call(self.printf,[self._указ(self.строитель,self._фмт_i64),val])
    return ЦЕЛОЕ(0)
   args=[self._выр(a) for a in в.аргументы]
   if в.имя in self.функции:return self.строитель.call(self.функции[в.имя],args)
   sig=tuple(a.type for a in args);prev=self.внешние.get(в.имя)
   if prev and prev[0]!=sig:raise ОшибкаКодогена(f"extern ABI mismatch '{в.имя}'")
   if not prev:self.внешние[в.имя]=(sig,ir.Function(self.модуль,ir.FunctionType(ЦЕЛОЕ,list(sig)),name=символ("abi.v1",в.имя)))
   return self.строитель.call(self.внешние[в.имя][1],args)
  raise ОшибкаКодогена(f"неподдерживаемый узел {type(в).__name__}")
 def _глоб(self,текст):
  data=bytearray(текст.encode("utf-8")+b"\0");arr=ir.ArrayType(БАЙТ,len(data));g=ir.GlobalVariable(self.модуль,arr,name=f".str.{self._счёт}");self._счёт+=1;g.linkage="internal";g.global_constant=True;g.initializer=ir.Constant(arr,data);return g
 @staticmethod
 def _указ(b,g):return b.gep(g,[I32(0),I32(0)],inbounds=True)
 def _бул(self,v):return v if v.type==БУЛЕВ else self.строитель.icmp_signed("!=",v,ЦЕЛОЕ(0))
