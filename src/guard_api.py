# -*- coding: utf-8 -*-
"""Машиночитаемый API Yadro Guard для интеграций (дашборд Hermes и др.).

    python -m src.guard_api scan    <файл> [--lang en|ru]
    python -m src.guard_api fix     <файл> [--lang en|ru]
    python -m src.guard_api report  <файл> [--lang en|ru]
    python -m src.guard_api analyze --stdin [--lang en|ru]   (JSON {"code": "..."} в stdin)
    python -m src.guard_api autofix --stdin [--lang en|ru]   (вернуть исправленный код)

Исходник может быть на русском или английском YadroLang: язык определяется
сам и переводится в канонический по токенам (номера строк сохраняются).
Ответ — ровно один JSON-объект. Коды выхода: 0 чисто, 2 утечка, 3 ошибка.
"""
import json
import re
import sys
from pathlib import Path

РАСШИРЕНИЯ = {".яд", ".yad", ".yd"}
МАКС_РАЗМЕР = 200_000

MSG = {
    "bad_ext": {"en": "Only YadroLang files are supported (.yad, .yd, .яд).",
                "ru": "Поддерживаются только файлы YadroLang (.yad, .yd, .яд)."},
    "not_found": {"en": "File not found.", "ru": "Файл не найден."},
    "too_big": {"en": "The code is too large (limit 200 KB).", "ru": "Код слишком большой (лимит 200 КБ)."},
    "empty": {"en": "Paste some code first.", "ru": "Сначала вставьте код."},
    "syntax": {"en": "The code could not be read: ", "ru": "Код не удалось разобрать: "},
    "no_fix": {"en": "No safe automatic fix exists for this leak. It has to be fixed by hand.",
               "ru": "Надёжной автопочинки нет — исправьте вручную."},
    "nothing": {"en": "Nothing to fix: no leak was found.", "ru": "Исправлять нечего — утечек нет."},
    "internal": {"en": "Internal analyzer error. Treat this code as unverified.",
                 "ru": "Внутренняя ошибка анализатора. Считайте код непроверенным."},
}


class ОшибкаВвода(ValueError):
    pass


def _файл(путь, lang):
    p = Path(путь)
    if p.suffix.lower() not in РАСШИРЕНИЯ:
        raise ОшибкаВвода(MSG["bad_ext"][lang])
    if not p.is_file():
        raise ОшибкаВвода(MSG["not_found"][lang])
    if p.stat().st_size > МАКС_РАЗМЕР:
        raise ОшибкаВвода(MSG["too_big"][lang])
    return p, p.read_text(encoding="utf-8")


def _проверить_текст(код, lang):
    if not isinstance(код, str) or not код.strip():
        raise ОшибкаВвода(MSG["empty"][lang])
    if len(код.encode("utf-8")) > МАКС_РАЗМЕР:
        raise ОшибкаВвода(MSG["too_big"][lang])
    return код


def _исходник_языка(код):
    from src import localize
    язык_кода = localize.detect_lang(код)
    канон = localize.to_canonical(код) if язык_кода == "en" else код
    return язык_кода, канон


# Честно: что движок СЕЙЧАС не ловит (подтверждено корпусом tests/ethics_gaps).
# Убирать пункт только вместе с исправлением в движке и зелёным тестом.
KNOWN_GAPS = {
    "en": ["Data printed with print() is not treated as a leak yet.",
           "The value returned by main() is not checked as program output yet.",
           "Hidden leaks through a variable changed inside an if/while that depends on a secret.",
           "Hidden leaks through a helper whose return value depends on a secret.",
           "Leaks that depend on how many times a loop runs."],
    "ru": ["Вывод через печать() пока не считается утечкой.",
           "Значение, которое возвращает старт(), пока не проверяется как вывод программы.",
           "Скрытые утечки через переменную, изменённую внутри если/пока, зависящих от секрета.",
           "Скрытые утечки через вспомогательную функцию, чей результат зависит от секрета.",
           "Утечки через количество итераций цикла."],
}

ОШИБКИ_ИСХОДНИКА = {
    "ОшибкаЛексера": {"en": "Syntax error", "ru": "Синтаксическая ошибка"},
    "ОшибкаПарсера": {"en": "Syntax error", "ru": "Синтаксическая ошибка"},
    "ОшибкаТипов": {"en": "Type error", "ru": "Ошибка типов"},
    "ОшибкаСемантики": {"en": "Program error", "ru": "Ошибка в программе"},
    "ОшибкаТочкиВхода": {"en": "The program needs exactly one main() function with no parameters",
                         "ru": "Нужна ровно одна функция старт() без параметров"},
}


def код_для(код, lang):
    return код.replace("ЯДРО-Э", "YADRO-E").replace("ЯДРО-Т", "YADRO-T") if lang == "en" else код


def _ошибка_исходника(e, lang):
    имя = type(e).__name__
    заголовок = ОШИБКИ_ИСХОДНИКА.get(имя, {"en": "The code could not be analyzed",
                                          "ru": "Код не удалось проанализировать"})[lang]
    строка = re.search(r"(?:строк[аи]|на)\s+(\d+)", str(e))
    return {"status": "error", "message": заголовок + (f" (line {строка.group(1)})" if строка and lang == "en"
                                                       else f" (строка {строка.group(1)})" if строка else ""),
            "detail": str(e)[:300]}


def _автофикс(код, язык_кода, канон, д, lang):
    """План фикса в языке пользователя; проверяется повторным анализом."""
    from src import autofix, localize
    план = autofix.предложить(канон, д)
    if not план:
        return None
    строки = код.splitlines()
    было = строки[план["строка"] - 1]
    сток = re.search(r"стока? '([^']+)'", д["message"]).group(1)
    стало, ok = autofix._обернуть_аргумент(было, localize.name_for(сток, язык_кода),
                                            localize.name_for(план["обёртка"], язык_кода))
    if not ok:
        return None
    строки[план["строка"] - 1] = стало
    новый = "\n".join(строки) + ("\n" if код.endswith("\n") else "")
    проверено = autofix._проверить(localize.to_canonical(новый) if язык_кода == "en" else новый)
    return {"wrapper": localize.name_for(план["обёртка"], язык_кода),
            "wrapper_human": localize.sanitizer_human(план["обёртка"], lang),
            "line": план["строка"], "before": было, "after": стало,
            "verified": проверено, "fixed_code": новый}


def анализ_текста(код, lang="en"):
    """Главная функция: исходник (ru/en) -> вердикт для людей. Без исключений наружу."""
    from src import autofix, localize, report_html
    from src.main import компилировать
    from src.этика import ЭтическаяОшибка, ЭтическийАнализатор
    from src.guard_impl import diagnostic
    from src.лексер import Лексер
    from src.синтаксис import Парсер
    from src import этика_v21 as политика
    код = _проверить_текст(код, lang)
    язык_кода, канон = _исходник_языка(код)
    база = {"lines": len(код.splitlines()), "code_language": язык_кода,
            "known_gaps": KNOWN_GAPS[lang]}
    try:
        компилировать(канон)
    except ЭтическаяОшибка as e:
        д = diagnostic(e, "input")
        метки = report_html._метки(д["message"])
        сток = re.search(r"стока? '([^']+)'", д["message"]) or re.search(r"вызывает '([^']+)'", д["message"])
        сток = сток.group(1) if сток else "?"
        истоки = report_html._источники(канон.splitlines(), set(метки))[:6]
        return {**база, "status": "leak", "code": код_для(д["code"], lang), "line": д["line"],
                "why": localize.why(д["code"], lang),
                "detail": д["message"],
                "labels": [localize.label_info(м, lang) for м in метки],
                "sink": {"name": localize.name_for(сток, язык_кода), "human": localize.sink_human(сток, lang)},
                "sources": [{"line": н, "name": localize.name_for(и, язык_кода),
                             "label": localize.label_info(м, lang)} for н, и, м in истоки],
                "quarantine": [{"label": localize.label_info(м, lang)["label"],
                                "options": [{"fn": localize.name_for(с, язык_кода),
                                             "human": localize.sanitizer_human(с, lang)}
                                            for с in sorted(политика.КОМПЛАЕНС.get(м, set()))]}
                               for м in метки],
                "autofix": _автофикс(код, язык_кода, канон, д, lang)}
    except Exception as e:
        return {**база, **_ошибка_исходника(e, lang)}
    ан = ЭтическийАнализатор()
    ан.проверить(Парсер(Лексер(канон).токены()).разобрать())
    return {**база, "status": "ok",
            "sanitized": [{"line": з.строка, "wrapper": localize.name_for(з.источник, язык_кода),
                           "label": localize.label_info(з.метка, lang)}
                          for з in ан.аудит_трейл if з.статус == "САНИТАЙЗ"]}


def анализ(путь, lang="ru"):
    """Совместимость: анализ файла."""
    try:
        p, код = _файл(путь, lang)
    except (ОшибкаВвода, OSError, UnicodeError) as e:
        return {"status": "error", "path": str(путь), "message": str(e)}
    return {"path": str(p.resolve()), **анализ_текста(код, lang)}


def исправить(путь, lang="ru"):
    р = анализ(путь, lang)
    if р["status"] != "leak":
        return {"status": р["status"], "written": None,
                "message": р.get("message", MSG["nothing"][lang])}
    фикс = р.get("autofix")
    if not фикс or not фикс["verified"]:
        return {"status": "leak", "written": None, "message": MSG["no_fix"][lang]}
    p = Path(путь)
    цель = p.with_suffix(".fixed" + p.suffix)
    цель.write_text(фикс["fixed_code"], encoding="utf-8")
    return {"status": "fixed", "written": str(цель.resolve()), "wrapper": фикс["wrapper"],
            "before": фикс["before"], "after": фикс["after"]}


def отчёт_текста(код, lang="en", имя="pasted code"):
    from src import report_html
    from src.version import VERSION
    р = анализ_текста(код, lang)
    if р["status"] == "error":
        return р
    return {"status": р["status"], "html": report_html.построить_из_результата(имя, код, р, VERSION, lang)}


def отчёт(путь, lang="ru"):
    try:
        p, код = _файл(путь, lang)
    except (ОшибкаВвода, OSError, UnicodeError) as e:
        return {"status": "error", "message": str(e)}
    return отчёт_текста(код, lang, str(p.resolve()))


def _из_stdin(lang):
    данные = json.loads(sys.stdin.read() or "{}")
    return данные.get("code", "")


def автофикс_текста(код, lang="en"):
    р = анализ_текста(код, lang)
    if р["status"] != "leak":
        return {"status": р["status"], "message": р.get("message", MSG["nothing"][lang])}
    ф = р.get("autofix")
    if not ф or not ф["verified"]:
        return {"status": "leak", "message": MSG["no_fix"][lang]}
    return {"status": "fixed", **ф}


ФАЙЛОВЫЕ = {"scan": анализ, "fix": исправить, "report": отчёт}
ТЕКСТОВЫЕ = {"analyze": анализ_текста, "autofix": автофикс_текста, "report-text": отчёт_текста}
КОДЫ = {"ok": 0, "fixed": 0, "leak": 2, "error": 3}


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    lang = "ru"
    if "--lang" in args:
        i = args.index("--lang")
        lang = args[i + 1] if i + 1 < len(args) and args[i + 1] in ("en", "ru") else "ru"
        del args[i:i + 2]
    try:
        if len(args) == 2 and args[0] in ТЕКСТОВЫЕ and args[1] == "--stdin":
            результат = ТЕКСТОВЫЕ[args[0]](_из_stdin(lang), lang)
        elif len(args) == 2 and args[0] in ФАЙЛОВЫЕ:
            результат = ФАЙЛОВЫЕ[args[0]](args[1], lang)
        else:
            результат = {"status": "error", "message": "usage: scan|fix|report <file> | analyze|autofix|report-text --stdin"}
    except ОшибкаВвода as e:
        результат = {"status": "error", "message": str(e)}
    except Exception as e:  # fail-closed: сбой = ошибка, никогда не «чисто»
        результат = {"status": "error", "message": MSG["internal"][lang], "detail": type(e).__name__}
    sys.stdout.write(json.dumps(результат, ensure_ascii=False))
    return КОДЫ.get(результат.get("status"), 3)


if __name__ == "__main__":
    raise SystemExit(main())
