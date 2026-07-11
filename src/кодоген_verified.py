# -*- coding: utf-8 -*-
import hashlib
from llvmlite import ir,binding as llvm
from src.синтаксис import Вернуть,Пусть,Присвоить,Если,Пока,Число,Строка,Булево,Имя,Бинарный,Вызов
I64,BOOL,BYTE,I32=ir.IntType(64),ir.IntType(1),ir.IntType(8),ir.IntType(32);PTR=BYTE.as_pointer();VOID=ir.VoidType()
ПРОФИЛИ_АРИФМЕТИКИ=frozenset({"default","checked"});I64_МИН=-(2**63)
class ОшибкаКодогена(Exception):pass
def тип(т):return {"i64":I64,"bool":BOOL,"string":PTR}[т]
def символ(префикс,имя):return f"yadro.{префикс}.{hashlib.sha256(имя.encode()).hexdigest()[:16]}"
class Кодоген:
 def __init__(self,symbol_mangler=None,arithmetic_profile="default"):
  if arithmetic_profile not in ПРОФИЛИ_АРИФМЕТИКИ:raise ОшибкаКодогена(f"неизвестный arithmetic profile '{arithmetic_profile}'")
  self.symbol_mangler=символ if symbol_mangler is None else symbol_mangler;self.arithmetic_profile=arithmetic_profile;self.модуль=ir.Module(name="ядро");self.модуль.triple=llvm.get_default_triple();self.ф={};self.ext={};self.скоуп={};self.b=None;self.n=0;self.printf=ir.Function(self.модуль,ir.FunctionType(I32,[PTR],var_arg=True),name="printf")
  self._trap=None
  if arithmetic_profile=="checked":self._создать_trap()
 def _создать_trap(self):
  intrinsic=ir.Function(self.модуль,ir.FunctionType(VOID,[]),name="llvm.trap")
  self._trap=ir.Function(self.модуль,ir.FunctionType(VOID,[]),name="yadro_checked_trap");self._trap.linkage="internal";b=ir.IRBuilder(self._trap.append_basic_block("entry"));b.call(intrinsic,[]);b.unreachable()
 def сгенерировать(self,прог):
  self.fi=self._глоб("%lld\n");self.fs=self._глоб("%s\n");self.fr=self._глоб("Результат старт(): %lld\n")
  for ф in прог.функции:self.ф[ф.имя]=ir.Function(self.модуль,ir.FunctionType(тип(ф.выведенный_тип_возврата),[тип(x) for x in ф.выведенные_типы_параметров]),name=self.symbol_mangler("fn",ф.имя))
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
 def _guard(self,bad,stem):
  fn=self.b.function;fail=fn.append_basic_block(f"{stem}.trap");ok=fn.append_basic_block(f"{stem}.ok");self.b.cbranch(bad,fail,ok);self.b.position_at_end(fail);self.b.call(self._trap,[]);self.b.unreachable();self.b.position_at_end(ok)
 def _checked_overflow(self,op,left,right):
  names={"+":"llvm.sadd.with.overflow.i64","-":"llvm.ssub.with.overflow.i64","*":"llvm.smul.with.overflow.i64"};name=names[op];intrinsic=self.модуль.globals.get(name)
  if intrinsic is None:intrinsic=ir.Function(self.модуль,ir.FunctionType(ir.LiteralStructType([I64,BOOL]),[I64,I64]),name=name)
  pair=self.b.call(intrinsic,[left,right],name="checked.pair");value=self.b.extract_value(pair,0,name="checked.value");overflow=self.b.extract_value(pair,1,name="checked.overflow");self._guard(overflow,"arith.overflow");return value
 def _checked_div(self,left,right):
  zero=self.b.icmp_signed("==",right,I64(0),name="div.zero");minimum=self.b.icmp_signed("==",left,I64(I64_МИН),name="div.minimum");minus_one=self.b.icmp_signed("==",right,I64(-1),name="div.minus_one");bad=self.b.or_(zero,self.b.and_(minimum,minus_one),name="div.invalid");self._guard(bad,"arith.div");return self.b.sdiv(left,right,name="checked.div")
 def _выр(self,у):
  if isinstance(у,Число):return I64(у.значение)
  if isinstance(у,Булево):return BOOL(1 if у.значение else 0)
  if isinstance(у,Строка):return self._ptr(self.b,self._глоб(у.значение))
  if isinstance(у,Имя):return self.b.load(self.скоуп[у.имя])
  if isinstance(у,Бинарный):
   л,п=self._выр(у.слева),self._выр(у.справа)
   if self.arithmetic_profile=="checked" and у.оп in "+-*":return self._checked_overflow(у.оп,л,п)
   if self.arithmetic_profile=="checked" and у.оп=="/":return self._checked_div(л,п)
   ops={"+":self.b.add,"-":self.b.sub,"*":self.b.mul,"/":self.b.sdiv};return ops[у.оп](л,п) if у.оп in ops else self.b.icmp_signed(у.оп,л,п)
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
   if not prev:self.ext[у.имя]=(sig,ir.Function(self.модуль,ir.FunctionType(I64,list(sig)),name=self.symbol_mangler("abi.v1",у.имя)))
   return self.b.call(self.ext[у.имя][1],а)
  raise ОшибкаКодогена(f"неподдерживаемый узел {type(у).__name__}")
 def _глоб(self,т):
  d=bytearray(т.encode()+b"\0");a=ir.ArrayType(BYTE,len(d));g=ir.GlobalVariable(self.модуль,a,name=f".str.{self.n}");self.n+=1;g.linkage="internal";g.global_constant=True;g.initializer=ir.Constant(a,d);return g
 @staticmethod
 def _ptr(b,g):return b.gep(g,[I32(0),I32(0)],inbounds=True)
 def _bool(self,v):return v if v.type==BOOL else self.b.icmp_signed("!=",v,I64(0))
