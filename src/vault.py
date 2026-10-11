# -*- coding: utf-8 -*-
"""Карантин-хранилище: настоящий секрет остаётся локально, наружу уходит токен.

    python -m src.vault put  --label УчетныеДанные   (секрет читается из stdin)
    python -m src.vault get  <токен> --i-have-mandate (выдать оригинал)
    python -m src.vault list                          (только метаданные)
    python -m src.vault forget <токен>

Защита:
- Шифрование Windows DPAPI (CryptProtectData): ключ привязан к учётной записи
  Windows, файл сейфа бесполезен на другом ПК/пользователе. Без сторонних либ.
- Fail-closed: если надёжного шифрования нет (не Windows), сейф ОТКАЗЫВАЕТСЯ
  сохранять — никогда не пишет секрет открытым текстом.
- Токен случайный (secrets.token_hex): по нему нельзя восстановить секрет.
- Выдача оригинала требует явного мандата и пишется в журнал выдач.
- Токен в формате yg_tok_<label>_<hex>: метка видна, значение — нет.
"""
import base64
import json
import os
import secrets
import sys
import time
from pathlib import Path

ВЕРСИЯ_СЕЙФА = 1
_МЕТКИ = {"ПДн", "Финансы", "Здоровье", "УчетныеДанные", "Локация"}
_ЭНТРОПИЯ = b"yadro-guard-vault-v1"


class ОшибкаСейфа(Exception):
    pass


# ---------- DPAPI ----------
def _шифр_доступен() -> bool:
    return os.name == "nt"


def _dpapi(данные: bytes, зашифровать: bool) -> bytes:
    if not _шифр_доступен():
        raise ОшибкаСейфа("надёжное шифрование недоступно на этой ОС: сейф отказывается хранить секреты")
    import ctypes
    from ctypes import wintypes

    class БЛОБ(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def блоб(b):
        буф = ctypes.create_string_buffer(b, len(b))
        return БЛОБ(len(b), ctypes.cast(буф, ctypes.POINTER(ctypes.c_char))), буф

    вход, _держать = блоб(данные)
    энтр, _держать2 = блоб(_ЭНТРОПИЯ)
    выход = БЛОБ()
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32
    CRYPTPROTECT_UI_FORBIDDEN = 0x1
    fn = crypt32.CryptProtectData if зашифровать else crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(вход), None, ctypes.byref(энтр), None, None,
            CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(выход))
    if not ok:
        raise ОшибкаСейфа("DPAPI не смог обработать данные (другой пользователь/ПК или файл повреждён)")
    try:
        return ctypes.string_at(выход.pbData, выход.cbData)
    finally:
        kernel32.LocalFree(выход.pbData)


# ---------- хранилище ----------
def путь_сейфа():
    база = os.environ.get("YADRO_VAULT_DIR") or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "yadro-guard")
    return Path(база) / "vault.json"


def _загрузить():
    п = путь_сейфа()
    if not п.exists():
        return {"version": ВЕРСИЯ_СЕЙФА, "items": {}, "audit": []}
    данные = json.loads(п.read_text(encoding="utf-8"))
    if данные.get("version") != ВЕРСИЯ_СЕЙФА or not isinstance(данные.get("items"), dict):
        raise ОшибкаСейфа("неизвестный формат сейфа")
    return данные


def _сохранить(данные):
    п = путь_сейфа()
    п.parent.mkdir(parents=True, exist_ok=True)
    временный = п.with_suffix(".tmp")
    временный.write_text(json.dumps(данные, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(временный, п)  # атомарно: сейф не бывает «наполовину записан»


def положить(секрет: str, метка: str) -> str:
    if метка not in _МЕТКИ:
        raise ОшибкаСейфа(f"неизвестная метка: {метка}")
    if not секрет:
        raise ОшибкаСейфа("пустой секрет")
    шифр = _dpapi(секрет.encode("utf-8"), True)  # падает ДО записи, если шифра нет
    токен = f"yg_tok_{метка}_{secrets.token_hex(16)}"
    данные = _загрузить()
    данные["items"][токен] = {"label": метка, "created": int(time.time()),
                              "blob": base64.b64encode(шифр).decode("ascii")}
    _сохранить(данные)
    return токен


def достать(токен: str, мандат: bool, причина: str = "") -> str:
    if not мандат:
        raise ОшибкаСейфа("выдача оригинала требует явного мандата (--i-have-mandate)")
    данные = _загрузить()
    запись = данные["items"].get(токен)
    if not запись:
        raise ОшибкаСейфа("токен не найден")
    секрет = _dpapi(base64.b64decode(запись["blob"]), False).decode("utf-8")
    данные["audit"].append({"token": токен, "at": int(time.time()), "reason": причина[:200]})
    _сохранить(данные)
    return секрет


def список():
    """Только метаданные: токен, метка, время. Значения не расшифровываются."""
    данные = _загрузить()
    return [{"token": т, "label": з["label"], "created": з["created"]} for т, з in данные["items"].items()]


def забыть(токен: str) -> bool:
    данные = _загрузить()
    было = данные["items"].pop(токен, None) is not None
    if было:
        _сохранить(данные)
    return было


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="yadro-guard vault")
    sub = p.add_subparsers(dest="cmd", required=True)
    put = sub.add_parser("put"); put.add_argument("--label", required=True)
    get = sub.add_parser("get"); get.add_argument("token")
    get.add_argument("--i-have-mandate", action="store_true"); get.add_argument("--reason", default="")
    sub.add_parser("list")
    fg = sub.add_parser("forget"); fg.add_argument("token")
    a = p.parse_args(argv)
    try:
        if a.cmd == "put":
            секрет = sys.stdin.read().rstrip("\r\n")  # не из аргументов: не светится в истории команд
            print(положить(секрет, a.label))
        elif a.cmd == "get":
            print(достать(a.token, a.i_have_mandate, a.reason))
        elif a.cmd == "list":
            print(json.dumps(список(), ensure_ascii=False, indent=1))
        else:
            print("удалено" if забыть(a.token) else "не найдено")
        return 0
    except ОшибкаСейфа as e:
        print(f"сейф: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
