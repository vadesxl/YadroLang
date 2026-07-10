# -*- coding: utf-8 -*-
"""Коммерческий CLI Yadro Guard для русского фронтенда."""
import argparse
import json
import re
import sys
from pathlib import Path

from src import main as компилятор
from src.лексер import Лексер, ОшибкаЛексера
from src.синтаксис import Парсер, ОшибкаПарсера
from src.этика import ЭтическийАнализатор, ЭтическаяОшибка
from src import этика_v21 as runtime

ВЕРСИЯ = "2.1.0-dev"
УСПЕХ, НАРУШЕНИЕ_ПОЛИТИКИ, ОШИБКА_ИСХОДНИКА, ВНУТРЕННЯЯ_ОШИБКА = 0, 2, 3, 4
ИЗВЕСТНЫЕ_МЕТКИ = frozenset(runtime.ВСЕ_МЕТКИ)
_BASE_ИСТОЧНИКИ = dict(runtime.ИСТОЧНИКИ)
_BASE_СТОКИ = dict(runtime.СТОКИ)
_BASE_САНИТАЙЗЕРЫ = set(runtime.САНИТАЙЗЕРЫ)
_BASE_КОМПЛАЕНС = {ключ: set(значение) for ключ, значение in runtime.КОМПЛАЕНС.items()}
_BASE_АРНОСТЬ = dict(компилятор.АРНОСТЬ_СИСТЕМНЫХ_API)


class ОшибкаПолитики(ValueError): pass


def сбросить_политику():
    runtime.ИСТОЧНИКИ.clear(); runtime.ИСТОЧНИКИ.update(_BASE_ИСТОЧНИКИ)
    runtime.СТОКИ.clear(); runtime.СТОКИ.update(_BASE_СТОКИ)
    runtime.САНИТАЙЗЕРЫ.clear(); runtime.САНИТАЙЗЕРЫ.update(_BASE_САНИТАЙЗЕРЫ)
    runtime.КОМПЛАЕНС.clear(); runtime.КОМПЛАЕНС.update({к: set(з) for к, з in _BASE_КОМПЛАЕНС.items()})
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.clear(); компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update(_BASE_АРНОСТЬ)
    компилятор.СИСТЕМНЫЕ_API = set(компилятор.АРНОСТЬ_СИСТЕМНЫХ_API)


def загрузить_политику(путь):
    данные = json.loads(Path(путь).read_text(encoding="utf-8"))
    if данные.get("version") != "1.0": raise ОшибкаПолитики("policy.version должна быть '1.0'")
    for ключ in ("sources", "sinks", "sanitizers"):
        if ключ in данные and not isinstance(данные[ключ], dict): raise ОшибкаПолитики(f"policy.{ключ} должна быть объектом")
    for имя, метка in данные.get("sources", {}).items():
        if not isinstance(имя, str) or метка not in ИЗВЕСТНЫЕ_МЕТКИ: raise ОшибкаПолитики(f"неверный source: {имя!r}")
    for имя, мандат in данные.get("sinks", {}).items():
        if not isinstance(имя, str) or not isinstance(мандат, str) or not мандат: raise ОшибкаПолитики(f"неверный sink: {имя!r}")
    for имя, метки in данные.get("sanitizers", {}).items():
        if not isinstance(имя, str) or not isinstance(метки, list) or not set(метки) <= ИЗВЕСТНЫЕ_МЕТКИ: raise ОшибкаПолитики(f"неверный sanitizer: {имя!r}")
    return данные


def применить_политику(данные):
    сбросить_политику()
    runtime.ИСТОЧНИКИ.update(данные.get("sources", {})); runtime.СТОКИ.update(данные.get("sinks", {}))
    for санитайзер, метки in данные.get("sanitizers", {}).items():
        runtime.САНИТАЙЗЕРЫ.add(санитайзер)
        for метка in метки: runtime.КОМПЛАЕНС.setdefault(метка, set()).add(санитайзер)
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 0 for имя in данные.get("sources", {})})
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 1 for имя in данные.get("sinks", {})})
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 1 for имя in данные.get("sanitizers", {})})
    компилятор.СИСТЕМНЫЕ_API = set(компилятор.АРНОСТЬ_СИСТЕМНЫХ_API)


def диагностика(ошибка, путь):
    текст = str(ошибка); строка = re.search(r"строка (\d+)", текст)
    return {"tool":"yadro-guard", "version":ВЕРСИЯ, "path":str(путь),
            "code":getattr(ошибка, "код", "ЯДРО-ИСХОДНИК"),
            "line":int(строка.group(1)) if строка else 1, "message":текст}


def sarif(запись=None):
    правила, результаты = [], []
    if запись:
        правила = [{"id":запись["code"], "name":запись["code"]}]
        результаты = [{"ruleId":запись["code"], "level":"error", "message":{"text":запись["message"]},
                       "locations":[{"physicalLocation":{"artifactLocation":{"uri":запись["path"]},
                                                            "region":{"startLine":запись["line"]}}}]}]
    return {"$schema":"https://json.schemastore.org/sarif-2.1.0.json", "version":"2.1.0",
            "runs":[{"tool":{"driver":{"name":"Yadro Guard", "version":ВЕРСИЯ, "rules":правила}}, "results":результаты}]}


def вывести(значение, формат, поток):
    if формат == "text":
        print(f'{значение["path"]}:{значение["line"]}: {значение["message"]}' if isinstance(значение, dict) and "message" in значение else значение, file=поток)
    elif формат == "json": print(json.dumps(значение, ensure_ascii=False, indent=2), file=поток)
    else: print(json.dumps(sarif(значение if isinstance(значение, dict) and "message" in значение else None), ensure_ascii=False, indent=2), file=поток)


def подготовить(args):
    сбросить_политику()
    if getattr(args, "policy", None): применить_политику(загрузить_политику(args.policy))
    return Path(args.source).read_text(encoding="utf-8")


def классифицировать(ошибка):
    if isinstance(ошибка, ЭтическаяОшибка): return НАРУШЕНИЕ_ПОЛИТИКИ
    if isinstance(ошибка, (OSError, UnicodeError, json.JSONDecodeError, ОшибкаПолитики,
                           компилятор.ОшибкаТочкиВхода, компилятор.ОшибкаСемантики,
                           ОшибкаПарсера, ОшибкаЛексера)): return ОШИБКА_ИСХОДНИКА
    return ВНУТРЕННЯЯ_ОШИБКА


def scan(args, stdout):
    компилятор.компилировать(подготовить(args)); вывести({"status":"ok", "path":args.source, "version":ВЕРСИЯ}, args.format, stdout)


def compile_command(args, stdout):
    ir = компилятор.компилировать(подготовить(args), выводить_ir=args.ir)
    if not args.ir: компилятор.собрать_нативно(ir, args.output)


def audit(args, stdout):
    ast = Парсер(Лексер(подготовить(args)).токены()).разобрать()
    компилятор._проверить_уникальность_функций(ast); компилятор._проверить_точку_входа(ast)
    компилятор._проверить_вызовы(ast); компилятор._проверить_выражения(ast)
    анализатор = ЭтическийАнализатор(); анализатор.проверить(ast)
    if args.format == "json": вывести({"status":"ok", "findings":[vars(з) for з in анализатор.аудит_трейл]}, "json", stdout)
    elif args.format == "sarif": вывести({"status":"ok"}, "sarif", stdout)
    else: print(анализатор.сгенерировать_аудит_отчет(), file=stdout)


def создать_parser():
    root = argparse.ArgumentParser(prog="yadro-guard"); sub = root.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False); common.add_argument("source"); common.add_argument("--policy"); common.add_argument("--format", choices=("text","json","sarif"), default="text")
    sub.add_parser("scan", parents=[common]); cp = sub.add_parser("compile", parents=[common]); cp.add_argument("-o","--output",default="ядро.o"); cp.add_argument("--ir",action="store_true")
    sub.add_parser("audit", parents=[common]); pp = sub.add_parser("policy"); psub = pp.add_subparsers(dest="policy_command",required=True); check = psub.add_parser("check"); check.add_argument("path"); sub.add_parser("version")
    return root


def run(argv=None, stdout=sys.stdout, stderr=sys.stderr):
    args = создать_parser().parse_args(argv)
    if args.command == "version": print(ВЕРСИЯ, file=stdout); return УСПЕХ
    if args.command == "policy":
        try: загрузить_политику(args.path); print(f"политика корректна: {args.path}", file=stdout); return УСПЕХ
        except Exception as ошибка: print(f"некорректная политика: {ошибка}", file=stderr); return классифицировать(ошибка)
    действие = {"scan":scan, "compile":compile_command, "audit":audit}[args.command]
    try: действие(args, stdout); return УСПЕХ
    except Exception as ошибка: вывести(диагностика(ошибка, args.source), args.format, stderr); return классифицировать(ошибка)
    finally: сбросить_политику()


def main(): raise SystemExit(run())
if __name__ == "__main__": main()
