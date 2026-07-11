# -*- coding: utf-8 -*-
"""Конвейер YadroLang: парсер, семантика, типы, этика, LLVM."""
import os,shutil,subprocess,sys,tempfile
from llvmlite import binding as llvm
from src.лексер import Лексер,ОшибкаЛексера
from src.синтаксис import Парсер,ОшибкаПарсера,Вызов,Число,Бинарный
from src.этика import ЭтическийАнализатор,ЭтическаяОшибка,СТОКИ,ИСТОЧНИКИ,САНИТАЙЗЕРЫ
from src.типы import ПроверкаТипов,ОшибкаТипов
from src.кодоген import Кодоген,ОшибкаКодогена
ТАЙМАУТ_TOOL=30
class ОшибкаТочкиВхода(Exception):pass
class ОшибкаСемантики(Exception):pass
def _проверить_точку_входа(ast):
 старты=[ф for ф in ast.функции if ф.имя=="старт"]
 if not старты:raise ОшибкаТочкиВхода("Нет точки входа: объявите 'старт'.")
 if len(старты)>1:raise ОшибкаТочкиВхода("'старт' должен быть объявлен один раз.")
 if старты[0].параметры:raise ОшибкаТочкиВхода("'старт' не принимает параметры.")
def _проверить_уникальность_функций(ast):
 известные=set()
 for ф in ast.функции:
  if ф.имя in известные:raise ОшибкаСемантики(f"Функция '{ф.имя}' объявлена повторно (строка {ф.строка}).")
  if ф.имя=="printf" or ф.имя.startswith("yadro_"):raise ОшибкаСемантики(f"Функция '{ф.имя}' конфликтует с runtime ABI (строка {ф.строка}).")
  известные.add(ф.имя)
АРНОСТЬ_СИСТЕМНЫХ_API={**{и:0 for и in ИСТОЧНИКИ},**{и:1 for и in САНИТАЙЗЕРЫ},**{и:1 for и in СТОКИ},"печать":1}
def _собрать(узел,тип,вывод):
 if isinstance(узел,тип):вывод.append(узел)
 значения=getattr(узел,"__dict__",None)
 if значения:
  for значение in значения.values():
   if isinstance(значение,list):
    for элемент in значение:_собрать(элемент,тип,вывод)
   elif hasattr(значение,"__dict__"):_собрать(значение,тип,вывод)
def _проверить_вызовы(ast):
 арность={ф.имя:len(ф.параметры) for ф in ast.функции}
 for ф in ast.функции:
  вызовы=[]
  for у in ф.тело:_собрать(у,Вызов,вызовы)
  for вызов in вызовы:
   ожидается=арность.get(вызов.имя,АРНОСТЬ_СИСТЕМНЫХ_API.get(вызов.имя))
   if ожидается is None:raise ОшибкаСемантики(f"Неизвестная функция '{вызов.имя}' (строка {вызов.строка}).")
   if len(вызов.аргументы)!=ожидается:raise ОшибкаСемантики(f"Функция '{вызов.имя}' ожидает {ожидается} арг., получено {len(вызов.аргументы)} (строка {вызов.строка}).")
I64_МИН=-(2**63);I64_МАКС=2**63-1
def _константа(узел):
 if isinstance(узел,Число):return узел.значение
 if not isinstance(узел,Бинарный):return None
 л,п=_константа(узел.слева),_константа(узел.справа)
 if л is None or п is None:return None
 if узел.оп=="+":return л+п
 if узел.оп=="-":return л-п
 if узел.оп=="*":return л*п
 if узел.оп=="/" and п!=0:return abs(л)//abs(п)*(-1 if (л<0)!=(п<0) else 1)
 return None
def _проверить_выражения(ast):
 for ф in ast.функции:
  числа=[];бинарные=[]
  for у in ф.тело:_собрать(у,Число,числа);_собрать(у,Бинарный,бинарные)
  for число in числа:
   if not I64_МИН<=число.значение<=I64_МАКС:raise ОшибкаСемантики(f"Число {число.значение} вне i64 (строка {число.строка}).")
  for б in бинарные:
   if б.оп!="/":continue
   делитель,делимое=_константа(б.справа),_константа(б.слева)
   if делитель==0:raise ОшибкаСемантики(f"Деление на ноль (строка {б.строка}).")
   if делимое==I64_МИН and делитель==-1:raise ОшибкаСемантики(f"Переполнение знакового i64 (строка {б.строка}).")
def компилировать(исходник,выводить_ir=False):
 ast=Парсер(Лексер(исходник).токены()).разобрать();_проверить_уникальность_функций(ast);_проверить_точку_входа(ast);_проверить_вызовы(ast);_проверить_выражения(ast);ПроверкаТипов(set(ИСТОЧНИКИ)|set(СТОКИ)|set(САНИТАЙЗЕРЫ)|{"печать"}).проверить(ast);ЭтическийАнализатор().проверить(ast);ir=Кодоген().сгенерировать(ast)
 if выводить_ir:print(ir)
 return ir
def _запустить_tool(команда,этап):
 try:return subprocess.run(команда,capture_output=True,text=True,timeout=ТАЙМАУТ_TOOL)
 except subprocess.TimeoutExpired as ошибка:raise RuntimeError(f"{этап} завис более {ТАЙМАУТ_TOOL}s: {os.path.basename(str(ошибка.cmd[0]))}") from ошибка
def _создать_windows_coff(модуль,выход,triple):
 clang=shutil.which("clang")
 if not clang:raise RuntimeError("Для Windows native object нужен поддерживаемый clang LLVM toolchain в PATH")
 with tempfile.TemporaryDirectory() as папка:
  путь_ir=os.path.join(папка,"yadro.ll")
  with open(путь_ir,"w",encoding="utf-8",newline="\n") as файл_ir:файл_ir.write(str(модуль))
  результат=_запустить_tool([clang,"-target",triple,"-x","ir","-c",путь_ir,"-o",выход],"clang COFF emission")
  if результат.returncode:raise RuntimeError(f"clang COFF emission завершился ошибкой: {результат.stderr.strip()}")
 with open(выход,"rb") as файл:
  if файл.read(2)!=b"\x64\x86":raise RuntimeError("clang не создал AMD64 COFF object")
def собрать_нативно(ir_код,выход="ядро.o"):
 for инициализатор in (getattr(llvm,"initialize",None),getattr(llvm,"initialize_native_target",None),getattr(llvm,"initialize_native_asmprinter",None)):
  if инициализатор:
   try:инициализатор()
   except Exception:pass
 triple=llvm.get_default_triple();target=llvm.Target.from_triple(triple);machine=target.create_target_machine();модуль=llvm.parse_assembly(ir_код);модуль.triple=triple;модуль.data_layout=str(machine.target_data);модуль.verify()
 if os.name=="nt":_создать_windows_coff(модуль,выход,triple)
 else:
  with open(выход,"wb") as файл:файл.write(machine.emit_object(модуль))
 print(f"[ЯДРО] Нативный объектник: {выход}")
def главная():
 if len(sys.argv)<2:print("Использование: python -m src.main файл.яд [--ir]");raise SystemExit(1)
 try:
  исходник=open(sys.argv[1],encoding="utf-8").read();ir=компилировать(исходник,"--ir" in sys.argv)
  if "--ir" not in sys.argv:собрать_нативно(ir)
 except (OSError,ОшибкаТочкиВхода,ОшибкаСемантики,ОшибкаТипов,ЭтическаяОшибка,ОшибкаПарсера,ОшибкаЛексера,ОшибкаКодогена,RuntimeError) as ошибка:print(f"[ЯДРО] Ошибка компиляции: {ошибка}");raise SystemExit(1)
 print("[ЯДРО] Компиляция завершена. Код - это закон.")
if __name__=="__main__":главная()
