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
from src import этика_v21 as политика_runtime
from src.кодоген import ОшибкаКодогена

ВЕРСИЯ = "2.1.0-dev"
УСПЕХ = 0
НАРУШЕНИЕ_ПОЛИТИКИ = 2
ОШИБКА_ИСХОДНИКА = 3
ВНУТРЕННЯЯ_ОШИБКА = 4
ИЗВЕСТНЫЕ_МЕТКИ = frozenset(политика_runtime.ВСЕ_МЕТКИ)


class ОшибкаПолитики(ValueError):
    pass


def загрузить_политику(путь):
    данные = json.loads(Path(путь).read_text(encoding="utf-8"))
    if данные.get("version") != "1.0":
        raise ОшибкаПолитики("policy.version должна быть '1.0'")
    for ключ in ("sources", "sinks", "sanitizers"):
        if ключ in данные and not isinstance(данные[ключ], dict):
            raise ОшибкаПолитики(f"policy.{ключ} должна быть объектом")
    for имя, метка in данные.get("sources", {}).items():
        if not isinstance(имя, str) or метка not in ИЗВЕСТНЫЕ_МЕТКИ:
            raise ОшибкаПолитики(f"некорректный источник: {имя!r} -> {метка!r}")
    for имя, мандат in данные.get("sinks", {}).items():
        if not isinstance(имя, str) or not isinstance(мандат, str) or not мандат:
            raise ОшибкаПолитики(f"некорректный сток: {имя!r}")
    for имя, метки in данные.get("sanitizers", {}).items():
        if not isinstance(имя, str) or not isinstance(метки, list) or not set(метки) <= ИЗВЕСТНЫЕ_МЕТКИ:
            raise ОшибкаПолитики(f"некорректный санитайзер: {имя!r}")
    return данные


def применить_политику(данные):
    политика_runtime.ИСТОЧНИКИ.update(данные.get("sources", {}))
    политика_runtime.СТОКИ.update(данные.get("sinks", {}))
    for санитайзер, метки in данные.get("sanitizers", {}).items():
        политика_runtime.САНИТАЙЗЕРЫ.add(санитайзер)
        for метка in метки:
            политика_runtime.КОМПЛАЕНС.setdefault(метка, set()).add(санитайзер)
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 0 for имя in данные.get("sources", {})})
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 1 for имя in данные.get("sinks", {})})
    компилятор.АРНОСТЬ_СИСТЕМНЫХ_API.update({имя: 1 for имя in данные.get("sanitizers", {})})
    компилятор.СИСТЕМНЫЕ_API = set(компилятор.АРНОСТЬ_СИСТЕМНЫХ_API)


def диагностика(ошибка, путь):
    текст = str(ошибка)
    строка = re.search(r"строка (\d+)", текст)
    return {"tool": "yadro-guard", "version": ВЕРСИЯ, "path": str(путь),
            "code": getattr(ошибка, "код", "ЯДРО-ИСХОДНИК"),
            "line": int(строка.group(1)) if строка else 1, "message": текст}


def в_sarif(запись):
    return {"$schema": "https://json.schemastore.org/sarif-2.1.0.json", "version": "2.1.0",
            "runs": [{"tool": {"driver": {"name": "Yadro Guard", "version": ВЕРСИЯ,
                                              "rules": [{"id": запись["code"], "name": запись["code"]}]}},
                      "results": [{"ruleId": запись["code"], "level": "error",
                                   "message": {"text": запись["message"]},
                                   "locations": [{"physicalLocation": {
                                       "artifactLocation": {"uri": запись["path"]},
                                       "region": {"startLine": запись["line"]}}}]}]}]}


def вывести(значение, формат, поток):
    if формат == "text":
        if isinstance(значение, dict) and "message" in значение:
            print(f'{значение["path"]}:{значение["line"]}: {значение["message"]}', file=поток)
        else:
            print(значение, file=поток)
    elif формат == "json":
        print(json.dumps(значение, ensure_ascii=False, indent=2), file=поток)
    else:
        print(json.dumps(в_sarif(значение), ensure_ascii=False, indent=2), file=поток)


def прочитать(путь):
    return Path(путь).read_text(encoding="utf-8")


def сканировать(args, stdout, stderr):
    try:
        if args.policy:
            применить_политику(загрузить_политику(args.policy))
        компилятор.компилировать(прочитать(args.source))
        вывести({"status": "ok", "path": args.source, "version": ВЕРСИЯ}, args.format, stdout)
        return УСПЕХ
    except ЭтическаяОшибка as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return НАРУШЕНИЕ_ПОЛИТИКИ
    except (OSError, UnicodeError, json.JSONDecodeError, ОшибкаПолитики,
            компилятор.ОшибкаТочкиВхода, компилятор.ОшибкаСемантики,
            ОшибкаПарсера, ОшибкаЛексера) as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ОШИБКА_ИСХОДНИКА
    except Exception as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ВНУТРЕННЯЯ_ОШИБКА


def компилировать(args, stdout, stderr):
    try:
        if args.policy:
            применить_политику(загрузить_политику(args.policy))
        ir_код = компилятор.компилировать(прочитать(args.source), выводить_ir=args.ir)
        if not args.ir:
            компилятор.собрать_нативно(ir_код, args.output)
        return УСПЕХ
    except ЭтическаяОшибка as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return НАРУШЕНИЕ_ПОЛИТИКИ
    except (OSError, UnicodeError, json.JSONDecodeError, ОшибкаПолитики,
            компилятор.ОшибкаТочкиВхода, компилятор.ОшибкаСемантики,
            ОшибкаПарсера, ОшибкаЛексера, ОшибкаКодогена) as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ОШИБКА_ИСХОДНИКА
    except Exception as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ВНУТРЕННЯЯ_ОШИБКА


def аудит(args, stdout, stderr):
    try:
        if args.policy:
            применить_политику(загрузить_политику(args.policy))
        ast = Парсер(Лексер(прочитать(args.source)).токены()).разобрать()
        компилятор._проверить_уникальность_функций(ast)
        компилятор._проверить_точку_входа(ast)
        компилятор._проверить_вызовы(ast)
        компилятор._проверить_выражения(ast)
        анализатор = ЭтическийАнализатор(); анализатор.проверить(ast)
        if args.format == "json":
            вывести({"status": "ok", "findings": [vars(запись) for запись in анализатор.аудит_трейл]}, "json", stdout)
        else:
            print(анализатор.сгенерировать_аудит_отчет(), file=stdout)
        return УСПЕХ
    except ЭтическаяОшибка as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return НАРУШЕНИЕ_ПОЛИТИКИ
    except (OSError, UnicodeError, json.JSONDecodeError, ОшибкаПолитики,
            компилятор.ОшибкаТочкиВхода, компилятор.ОшибкаСемантики,
            ОшибкаПарсера, ОшибкаЛексера) as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ОШИБКА_ИСХОДНИКА
    except Exception as ошибка:
        вывести(диагностика(ошибка, args.source), args.format, stderr); return ВНУТРЕННЯЯ_ОШИБКА


def создать_parser():
    root = argparse.ArgumentParser(prog="yadro-guard")
    sub = root.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("source"); common.add_argument("--policy")
    common.add_argument("--format", choices=("text", "json", "sarif"), default="text")
    sub.add_parser("scan", parents=[common])
    cp = sub.add_parser("compile", parents=[common]); cp.add_argument("-o", "--output", default="ядро.o"); cp.add_argument("--ir", action="store_true")
    ap = sub.add_parser("audit", parents=[common]); ap.set_defaults(format="text")
    pp = sub.add_parser("policy"); psub = pp.add_subparsers(dest="policy_command", required=True)
    check = psub.add_parser("check"); check.add_argument("path")
    sub.add_parser("version")
    return root


def run(argv=None, stdout=sys.stdout, stderr=sys.stderr):
    args = создать_parser().parse_args(argv)
    if args.command == "version":
        print(ВЕРСИЯ, file=stdout); return УСПЕХ
    if args.command == "policy":
        try:
            загрузить_политику(args.path); print(f"политика корректна: {args.path}", file=stdout); return УСПЕХ
        except (OSError, UnicodeError, json.JSONDecodeError, ОшибкаПолитики) as ошибка:
            print(f"некорректная политика: {ошибка}", file=stderr); return ОШИБКА_ИСХОДНИКА
    if args.command == "scan": return сканировать(args, stdout, stderr)
    if args.command == "compile": return компилировать(args, stdout, stderr)
    return аудит(args, stdout, stderr)


def main():
    raise SystemExit(run())


if __name__ == "__main__":
    main()
