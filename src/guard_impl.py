# -*- coding: utf-8 -*-
import argparse,json,re,sys
from pathlib import Path
from src import main as compiler
from src.лексер import Лексер,ОшибкаЛексера
from src.синтаксис import Парсер,ОшибкаПарсера
from src.этика import ЭтическийАнализатор,ЭтическаяОшибка
from src import этика_v21 as runtime
from src.version import VERSION
ВЕРСИЯ=VERSION;УСПЕХ,НАРУШЕНИЕ_ПОЛИТИКИ,ОШИБКА_ИСХОДНИКА,ВНУТРЕННЯЯ_ОШИБКА=0,2,3,4
ИЗВЕСТНЫЕ=frozenset(runtime.ВСЕ_МЕТКИ);_И=dict(runtime.ИСТОЧНИКИ);_С=dict(runtime.СТОКИ);_З=set(runtime.САНИТАЙЗЕРЫ);_К={k:set(v) for k,v in runtime.КОМПЛАЕНС.items()};_А=dict(compiler.АРНОСТЬ_СИСТЕМНЫХ_API)
class ОшибкаПолитики(ValueError):pass
def сбросить():
 runtime.ИСТОЧНИКИ.clear();runtime.ИСТОЧНИКИ.update(_И);runtime.СТОКИ.clear();runtime.СТОКИ.update(_С);runtime.САНИТАЙЗЕРЫ.clear();runtime.САНИТАЙЗЕРЫ.update(_З);runtime.КОМПЛАЕНС.clear();runtime.КОМПЛАЕНС.update({k:set(v) for k,v in _К.items()});compiler.АРНОСТЬ_СИСТЕМНЫХ_API.clear();compiler.АРНОСТЬ_СИСТЕМНЫХ_API.update(_А);compiler.СИСТЕМНЫЕ_API=set(compiler.АРНОСТЬ_СИСТЕМНЫХ_API)
def загрузить(path):
 data=json.loads(Path(path).read_text(encoding="utf-8"));unknown=set(data)-{"version","sources","sinks","sanitizers"}
 if unknown:raise ОшибкаПолитики(f"неизвестные поля: {sorted(unknown)}")
 if data.get("version")!="1.0":raise ОшибкаПолитики("version должна быть 1.0")
 reserved=set(_И)|set(_С)|set(_З)
 for key in ("sources","sinks","sanitizers"):
  if key in data and not isinstance(data[key],dict):raise ОшибкаПолитики(f"{key} должен быть объектом")
 for name,label in data.get("sources",{}).items():
  if label not in ИЗВЕСТНЫЕ or name in reserved:raise ОшибкаПолитики(f"неверный source: {name}")
 for name,cap in data.get("sinks",{}).items():
  if not isinstance(cap,str) or not cap or name in reserved:raise ОшибкаПолитики(f"неверный sink: {name}")
 for name,labels in data.get("sanitizers",{}).items():
  if not isinstance(labels,list) or not set(labels)<=ИЗВЕСТНЫЕ or name in reserved:raise ОшибкаПолитики(f"неверный sanitizer: {name}")
 return data
def применить(data):
 сбросить();runtime.ИСТОЧНИКИ.update(data.get("sources",{}));runtime.СТОКИ.update(data.get("sinks",{}))
 for name,labels in data.get("sanitizers",{}).items():
  runtime.САНИТАЙЗЕРЫ.add(name)
  for label in labels:runtime.КОМПЛАЕНС.setdefault(label,set()).add(name)
 compiler.АРНОСТЬ_СИСТЕМНЫХ_API.update({n:0 for n in data.get("sources",{})});compiler.АРНОСТЬ_СИСТЕМНЫХ_API.update({n:1 for n in data.get("sinks",{})});compiler.АРНОСТЬ_СИСТЕМНЫХ_API.update({n:1 for n in data.get("sanitizers",{})});compiler.СИСТЕМНЫЕ_API=set(compiler.АРНОСТЬ_СИСТЕМНЫХ_API)
def diagnostic(error,path):
 text=str(error);m=re.search(r"строка (\d+)",text);return {"tool":"yadro-guard","version":VERSION,"path":str(Path(path).resolve()),"code":getattr(error,"код","ЯДРО-ИСХОДНИК"),"line":int(m.group(1)) if m else 1,"message":text}
def sarif(item=None):
 rules=[];results=[]
 if item:rules=[{"id":item["code"],"name":item["code"]}];results=[{"ruleId":item["code"],"level":"error","message":{"text":item["message"]},"locations":[{"physicalLocation":{"artifactLocation":{"uri":Path(item["path"]).as_uri()},"region":{"startLine":item["line"]}}}]}]
 return {"$schema":"https://json.schemastore.org/sarif-2.1.0.json","version":"2.1.0","runs":[{"tool":{"driver":{"name":"Yadro Guard","version":VERSION,"rules":rules}},"results":results}]}
def emit(v,fmt,s):
 if fmt=="json":print(json.dumps(v,ensure_ascii=False,indent=2),file=s)
 elif fmt=="sarif":print(json.dumps(sarif(v if "message" in v else None),ensure_ascii=False,indent=2),file=s)
 else:print(f'{v["path"]}:{v["line"]}: {v["message"]}' if "message" in v else v,file=s)
def классифицировать(e):
 if isinstance(e,ЭтическаяОшибка):return НАРУШЕНИЕ_ПОЛИТИКИ
 if isinstance(e,(OSError,UnicodeError,json.JSONDecodeError,ОшибкаПолитики,compiler.ОшибкаТочкиВхода,compiler.ОшибкаСемантики,ОшибкаПарсера,ОшибкаЛексера)):return ОШИБКА_ИСХОДНИКА
 return ВНУТРЕННЯЯ_ОШИБКА
def parser():
 root=argparse.ArgumentParser(prog="yadro-guard");root.add_argument("--version",action="store_true");sub=root.add_subparsers(dest="command");common=argparse.ArgumentParser(add_help=False);common.add_argument("source");common.add_argument("--policy");common.add_argument("--format",choices=("text","json","sarif"),default="text");sub.add_parser("scan",parents=[common]);cp=sub.add_parser("compile",parents=[common]);cp.add_argument("-o","--output",default="ядро.o");cp.add_argument("--ir",action="store_true");sub.add_parser("audit",parents=[common]);pp=sub.add_parser("policy");ps=pp.add_subparsers(dest="policy_command",required=True);c=ps.add_parser("check");c.add_argument("path");sub.add_parser("version");return root
def run(argv=None,stdout=sys.stdout,stderr=sys.stderr):
 args=parser().parse_args(argv)
 if args.version or args.command=="version":print(VERSION,file=stdout);return УСПЕХ
 if not args.command:parser().print_help(stderr);return ОШИБКА_ИСХОДНИКА
 if args.command=="policy":
  try:загрузить(args.path);print(f"политика корректна: {args.path}",file=stdout);return УСПЕХ
  except Exception as e:print(f"некорректная политика: {e}",file=stderr);return классифицировать(e)
 try:
  сбросить()
  if args.policy:применить(загрузить(args.policy))
  source=Path(args.source).read_text(encoding="utf-8")
  if args.command=="scan":compiler.компилировать(source);emit({"status":"ok","path":str(Path(args.source).resolve()),"version":VERSION},args.format,stdout)
  elif args.command=="compile":
   ir=compiler.компилировать(source,выводить_ir=args.ir)
   if not args.ir:compiler.собрать_нативно(ir,args.output)
  else:
   ast=Парсер(Лексер(source).токены()).разобрать();compiler._проверить_уникальность_функций(ast);compiler._проверить_точку_входа(ast);compiler._проверить_вызовы(ast);compiler._проверить_выражения(ast);an=ЭтическийАнализатор();an.проверить(ast);emit({"status":"ok","findings":[vars(x) for x in an.аудит_трейл]},args.format,stdout) if args.format!="text" else print(an.сгенерировать_аудит_отчет(),file=stdout)
  return УСПЕХ
 except BrokenPipeError:return УСПЕХ
 except Exception as e:emit(diagnostic(e,args.source),args.format,stderr);return классифицировать(e)
 finally:сбросить()
def main():raise SystemExit(run())
