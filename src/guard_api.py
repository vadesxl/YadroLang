# -*- coding: utf-8 -*-
"""Машиночитаемый API Yadro Guard для интеграций (дашборд Hermes и др.).

    python -m src.guard_api scan   <файл>   -> JSON-вердикт с человеческими метками
    python -m src.guard_api fix    <файл>   -> записать <файл>.fixed.<ext>, JSON
    python -m src.guard_api report <файл>   -> {"html": ...} самодостаточный отчёт

Всегда печатает ровно один JSON-объект в stdout. Код выхода: 0 чисто,
2 утечка, 3 ошибка исходника/ввода. Внутренние детали стека наружу не уходят.
"""
import json
import re
import sys
from pathlib import Path

РАСШИРЕНИЯ = {".яд", ".yad", ".yd"}
МАКС_РАЗМЕР = 1_000_000


def _метка_людям(м):
    from src import report_html
    ярлык, иконка, цвет, пояснение = report_html.человек_метка(м)
    return {"id": м, "label": ярлык, "icon": иконка, "color": цвет, "about": пояснение}


def _карантин(метки):
    from src import этика_v21 as политика
    from src import report_html
    return [{"label": _метка_людям(м)["label"],
             "options": [{"fn": с, "human": report_html.САНИТАЙЗЕР_ЛЮДЯМ.get(с, с)}
                         for с in sorted(политика.КОМПЛАЕНС.get(м, set()))]}
            for м in метки]


def прочитать(путь):
    p = Path(путь)
    if p.suffix.lower() not in РАСШИРЕНИЯ:
        raise ValueError(f"поддерживаются только файлы {sorted(РАСШИРЕНИЯ)}")
    if not p.is_file():
        raise ValueError("файл не найден")
    if p.stat().st_size > МАКС_РАЗМЕР:
        raise ValueError("файл слишком большой")
    return p, p.read_text(encoding="utf-8")


def анализ(путь):
    """Полный разбор файла в dict (без исключений наружу)."""
    from src import report_html, autofix
    from src.main import компилировать
    from src.этика import ЭтическаяОшибка, ЭтическийАнализатор
    from src.guard_impl import diagnostic
    from src.лексер import Лексер
    from src.синтаксис import Парсер
    try:
        p, исходник = прочитать(путь)
    except (ValueError, OSError, UnicodeError) as e:
        return {"status": "error", "path": str(путь), "message": str(e)}
    база = {"path": str(p.resolve()), "lines": len(исходник.splitlines())}
    try:
        компилировать(исходник)
    except ЭтическаяОшибка as e:
        д = diagnostic(e, p)
        метки = report_html._метки(д["message"])
        сток = re.search(r"стока? '([^']+)'", д["message"]) or re.search(r"вызывает '([^']+)'", д["message"])
        сток = сток.group(1) if сток else "?"
        план = autofix.предложить(исходник, д)
        return {**база, "status": "leak", "code": д["code"], "line": д["line"],
                "message": д["message"],
                "why": report_html.ПОЯСНЕНИЕ.get(д["code"], "Нарушение политики потоков данных."),
                "labels": [_метка_людям(м) for м in метки],
                "sink": {"name": сток, "human": report_html.человек_сток(сток)},
                "sources": [{"line": н, "name": и, "label": _метка_людям(м)}
                            for н, и, м in report_html._источники(исходник.splitlines(), set(метки))[:6]],
                "quarantine": _карантин(метки),
                "autofix": ({k: план[k] for k in ("обёртка", "строка", "было", "стало", "проверено")}
                            if план else None)}
    except Exception as e:  # синтаксис, типы, точка входа
        return {**база, "status": "error", "message": str(e)[:300]}
    ast = Парсер(Лексер(исходник).токены()).разобрать()
    ан = ЭтическийАнализатор()
    ан.проверить(ast)
    return {**база, "status": "ok",
            "sanitized": [{"line": з.строка, "wrapper": з.источник, "label": _метка_людям(з.метка)}
                          for з in ан.аудит_трейл if з.статус == "САНИТАЙЗ"]}


def исправить(путь):
    from src import autofix
    результат = анализ(путь)
    if результат["status"] != "leak":
        return {"status": результат["status"], "written": None, "message": результат.get("message", "нечего исправлять")}
    p, исходник = прочитать(путь)
    from src.main import компилировать
    from src.этика import ЭтическаяОшибка
    from src.guard_impl import diagnostic
    try:
        компилировать(исходник)
        return {"status": "ok", "written": None}
    except ЭтическаяОшибка as e:
        план = autofix.предложить(исходник, diagnostic(e, p))
    if not план or not план["проверено"]:
        return {"status": "leak", "written": None, "message": "надёжной авто-починки нет"}
    цель = p.with_suffix(".fixed" + p.suffix)
    цель.write_text(план["новый_исходник"], encoding="utf-8")
    return {"status": "fixed", "written": str(цель.resolve()), "wrapper": план["обёртка"],
            "before": план["было"], "after": план["стало"]}


def отчёт(путь):
    from src import report_html
    from src.version import VERSION
    р = анализ(путь)
    if р["status"] == "error":
        return р
    p, исходник = прочитать(путь)
    д = None
    if р["status"] == "leak":
        д = {"code": р["code"], "line": р["line"], "message": р["message"], "_исходник": исходник}
    return {"status": р["status"], "html": report_html.построить(str(p.resolve()), исходник, д, None, VERSION)}


КОМАНДЫ = {"scan": анализ, "fix": исправить, "report": отчёт}
КОДЫ = {"ok": 0, "fixed": 0, "leak": 2, "error": 3}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] not in КОМАНДЫ:
        print(json.dumps({"status": "error", "message": "usage: scan|fix|report <file>"}, ensure_ascii=False))
        return 3
    try:
        результат = КОМАНДЫ[args[0]](args[1])
    except Exception as e:  # fail-closed: внутренний сбой = ошибка, не «чисто»
        результат = {"status": "error", "message": f"внутренняя ошибка: {type(e).__name__}"}
    sys.stdout.write(json.dumps(результат, ensure_ascii=False))
    return КОДЫ.get(результат.get("status"), 3)


if __name__ == "__main__":
    raise SystemExit(main())
