# -*- coding: utf-8 -*-
"""Конвейер YadroLang: парсер, семантика, типы, этика, LLVM."""
import argparse,os,shutil,subprocess,sys,tempfile
from llvmlite import binding as llvm
from src.лексер import Лексер,ОшибкаЛексера
from src.синтаксис import Парсер,ОшибкаПарсера,Вызов,Число,Бинарный
from src.этика import ЭтическийАнализатор,ЭтическаяОшибка,СТОКИ,ИСТОЧНИКИ,САНИТАЙЗЕРЫ
from src.типы import ПроверкаТипов,ОшибкаТипов
from src.кодоген import Кодоген,ОшибкаКодогена
ТАЙМАУТ_TOOL=30;ПРОФИЛИ_АРИФМЕТИКИ=frozenset({"default","checked"});МАКС_ГЛУБИНА_КОНСТАНТЫ=256
class ОшибкаТочкиВхода(Exception):pass
class ОшибкаСемантики(Exception):pass
class ОшибкаПрофиляАрифметики(ОшибкаСемантики):код="ЯДРО-А1000"
class ОшибкаCheckedАрифметики(ОшибкаСемантики):код="ЯДРО-А1001"
class ОшибкаГлубиныАрифметики(ОшибкаСемантики):код="ЯДРО-А1002"
_КОНСТАНТА_СЛИШКОМ_ГЛУБОКА=object()
def _проверить_профиль(арифметика):
 if not isinstance(арифметика,str) or арифметика not in ПРОФИЛИ_АРИФМЕТИКИ:raise ОшибкаПрофиляАрифметики("Неизвестный arithmetic profile.")
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
I64_МИН=-(2**63);I64_МАКС=2**63-1;I64_МОДУЛЬ=2**64
def _i64_wrap(значение):return ((значение-I64_МИН)%I64_МОДУЛЬ)+I64_МИН
def _константа(узел,глубина=0,wrap_i64=False):
 if глубина>МАКС_ГЛУБИНА_КОНСТАНТЫ:return _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА
 if isinstance(узел,Число):return узел.значение
 if not isinstance(узел,Бинарный):return None
 л,п=_константа(узел.слева,глубина+1,wrap_i64),_константа(узел.справа,глубина+1,wrap_i64)
 if л is _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА or п is _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА:return _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА
 if л is None or п is None:return None
 if узел.оп=="+":значение=л+п
 elif узел.оп=="-":значение=л-п
 elif узел.оп=="*":значение=л*п
 elif узел.оп=="/" and п!=0:значение=abs(л)//abs(п)*(-1 if (л<0)!=(п<0) else 1)
 else:return None
 return _i64_wrap(значение) if wrap_i64 else значение
def _ошибка_глубины(б):raise ОшибкаГлубиныАрифметики(f"Превышен предел анализа arithmetic expression (строка {б.строка}).")
def _проверить_выражения(ast,арифметика="default"):
 for ф in ast.функции:
  числа=[];бинарные=[]
  for у in ф.тело:_собрать(у,Число,числа);_собрать(у,Бинарный,бинарные)
  for число in числа:
   if not I64_МИН<=число.значение<=I64_МАКС:raise ОшибкаСемантики(f"Число {число.значение} вне i64 (строка {число.строка}).")
  for б in бинарные:
   wrap=арифметика=="default";делитель,делимое=_константа(б.справа,wrap_i64=wrap),_константа(б.слева,wrap_i64=wrap)
   if б.оп=="/":
    if делитель is _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА or делимое is _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА:_ошибка_глубины(б)
    if делитель==0:raise ОшибкаСемантики(f"Деление на ноль (строка {б.строка}).")
    if делимое==I64_МИН and делитель==-1:raise ОшибкаСемантики(f"Переполнение знакового i64 (строка {б.строка}).")
   if арифметика=="checked" and б.оп in "+-*":
    значение=_константа(б)
    if значение is _КОНСТАНТА_СЛИШКОМ_ГЛУБОКА:_ошибка_глубины(б)
    if значение is not None and not I64_МИН<=значение<=I64_МАКС:raise ОшибкаCheckedАрифметики(f"Переполнение checked i64 (строка {б.строка}).")
def компилировать(исходник,выводить_ir=False,арифметика="default"):
 _проверить_профиль(арифметика);ast=Парсер(Лексер(исходник).токены()).разобрать();_проверить_уникальность_функций(ast);_проверить_точку_входа(ast);_проверить_вызовы(ast);_проверить_выражения(ast,арифметика);ПроверкаТипов(set(ИСТОЧНИКИ)|set(СТОКИ)|set(САНИТАЙЗЕРЫ)|{"печать"}).проверить(ast);ЭтическийАнализатор().проверить(ast);ir=Кодоген(arithmetic_profile=арифметика).сгенерировать(ast)
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
def _разобрать_cli(argv):
 parser=argparse.ArgumentParser(prog="python -m src.main",allow_abbrev=False);parser.add_argument("source");parser.add_argument("--ir",action="store_true");parser.add_argument("--checked-arithmetic",action="store_true");return parser.parse_args(argv)
def главная(argv=None):
 args=_разобрать_cli(sys.argv[1:] if argv is None else argv)
 try:
  исходник=open(args.source,encoding="utf-8").read();профиль="checked" if args.checked_arithmetic else "default";ir=компилировать(исходник,args.ir,профиль)
  if not args.ir:собрать_нативно(ir)
 except (OSError,ОшибкаТочкиВхода,ОшибкаСемантики,ОшибкаТипов,ЭтическаяОшибка,ОшибкаПарсера,ОшибкаЛексера,ОшибкаКодогена,RuntimeError) as ошибка:print(f"[ЯДРО] Ошибка компиляции: {ошибка}");raise SystemExit(1)
 print("[ЯДРО] Компиляция завершена. Код - это закон.")
if __name__=="__main__":главная()
