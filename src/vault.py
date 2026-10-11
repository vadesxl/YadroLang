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
_МЕТКА_EN_ТОКЕНА = {"ПДн": "PII", "Финансы": "Financial", "Здоровье": "Health",
                    "УчетныеДанные": "Credentials", "Локация": "Location"}
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
    # Токен только ASCII: он уходит в HTTP-заголовки, URL и JSON чужих сервисов.
    токен = f"yg_tok_{_МЕТКА_EN_ТОКЕНА[метка]}_{secrets.token_hex(16)}"
    данные = _загрузить()
    данные["items"][токен] = {"label": метка, "created": int(time.time()),
                              "blob": base64.b64encode(шифр).decode("ascii")}
    _сохранить(данные)
    return токен


def положить_уникально(секрет: str, метка: str, отпечаток: str, название: str = "") -> str:
    """Как положить(), но один и тот же секрет (по SHA-256) хранится один раз."""
    данные = _загрузить()
    for токен, запись in данные["items"].items():
        if запись.get("fp") == отпечаток:
            return токен
    токен = положить(секрет, метка)
    данные = _загрузить()
    данные["items"][токен]["fp"] = отпечаток
    данные["items"][токен]["title"] = название[:80]
    данные["items"][токен]["source"] = "runtime-quarantine"
    _сохранить(данные)
    return токен


_МЕТКА_EN = {"ПДн": "PII", "Финансы": "Financial", "Здоровье": "Health",
             "УчетныеДанные": "Credentials", "Локация": "Location"}
МАКС_ДЛЯ_СВЕРКИ = 500
МАКС_ФАЙЛ_ДЛЯ_СВЕРКИ = 4096


def known_values():
    """(значение, метка_en, название) для точного поиска своих секретов в трафике агентов.
    Расшифровка только в памяти процесса; наружу значения не уходят."""
    if not _шифр_доступен() or not путь_сейфа().exists():
        return []
    out = []
    for запись in list(_загрузить()["items"].values())[:МАКС_ДЛЯ_СВЕРКИ]:
        if запись.get("deleted"):
            continue
        if запись.get("kind") == "file":          # маленькие текстовые файлы (.env, ключи) тоже ищем в трафике
            if запись.get("size", 0) > МАКС_ФАЙЛ_ДЛЯ_СВЕРКИ:
                continue
            try:
                текст = _dpapi(base64.b64decode(запись["blob"]), False).decode("utf-8").strip()
            except (ОшибкаСейфа, ValueError):
                continue
            if len(текст) >= 16:
                out.append((текст, _МЕТКА_EN.get(запись["label"], "Credentials"),
                            запись.get("title") or "A file from your vault"))
            continue
        try:
            значение = _dpapi(base64.b64decode(запись["blob"]), False).decode("utf-8")
        except (ОшибкаСейфа, ValueError):
            continue
        out.append((значение, _МЕТКА_EN.get(запись["label"], "Credentials"),
                    запись.get("title") or "A secret from your vault"))
    return out


def достать(токен: str, мандат: bool, причина: str = "") -> str:
    if not мандат:
        raise ОшибкаСейфа("выдача оригинала требует явного мандата (--i-have-mandate)")
    данные = _загрузить()
    запись = данные["items"].get(токен)
    if not запись or запись.get("deleted"):         # из корзины значение не выдаётся
        raise ОшибкаСейфа("токен не найден")
    секрет = _dpapi(base64.b64decode(запись["blob"]), False).decode("utf-8")
    данные["audit"].append({"token": токен, "at": int(time.time()), "reason": причина[:200]})
    _сохранить(данные)
    return секрет


def список(с_корзиной: bool = False):
    """Только метаданные: токен, метка, время. Значения не расшифровываются."""
    данные = _загрузить()
    if _очистить_корзину(данные):
        _сохранить(данные)
    out = []
    for т, з in данные["items"].items():
        if з.get("deleted") and not с_корзиной:
            continue
        d = {"token": т, "label": _МЕТКА_EN.get(з["label"], з["label"]), "created": з["created"],
             "title": з.get("title", ""), "source": з.get("source", "manual")}
        if с_корзиной:
            d.update(kind=з.get("kind", "text"), filename=з.get("filename", ""), size=з.get("size", 0),
                     changed=з.get("changed", 0), deleted=з.get("deleted", 0))
        out.append(d)
    return out


def забыть(токен: str) -> bool:
    данные = _загрузить()
    было = данные["items"].pop(токен, None) is not None
    if было:
        _сохранить(данные)
    return было


# ---------- управление записями: файлы, имя, замена, корзина ----------
МАКС_ФАЙЛ = 10 * 1024 * 1024          # 10 МБ: DPAPI и JSON-сейф рассчитаны на небольшие файлы
МАКС_ИМЯ = 80
КОРЗИНА_ДНЕЙ = 30


def _запись(данные, токен: str):
    запись = данные["items"].get(токен)
    if not запись:
        raise ОшибкаСейфа("запись не найдена")
    return запись


def _имя_файла(имя: str) -> str:
    """Только имя, без папок и запрещённых в Windows символов (защита от path traversal)."""
    имя = (имя or "").replace("\\", "/").split("/")[-1]
    имя = "".join("_" if (ord(c) < 32 or c in '<>:"|?*') else c for c in имя).strip(" .")
    return (имя or "file")[:120]


def положить_файл(содержимое: bytes, имя_файла: str, метка: str, название: str = "") -> str:
    """Файл шифруется целиком (DPAPI). Наружу — только токен и метаданные."""
    if not isinstance(содержимое, (bytes, bytearray)) or not содержимое:
        raise ОшибкаСейфа("пустой файл")
    if len(содержимое) > МАКС_ФАЙЛ:
        raise ОшибкаСейфа("файл больше 10 МБ")
    if метка not in _МЕТКИ:
        raise ОшибкаСейфа(f"неизвестная метка: {метка}")
    import hashlib
    шифр = _dpapi(bytes(содержимое), True)
    токен = f"yg_tok_{_МЕТКА_EN_ТОКЕНА[метка]}_{secrets.token_hex(16)}"
    имя = _имя_файла(имя_файла)
    данные = _загрузить()
    данные["items"][токен] = {"label": метка, "created": int(time.time()), "kind": "file",
                              "blob": base64.b64encode(шифр).decode("ascii"), "filename": имя,
                              "size": len(содержимое), "sha256": hashlib.sha256(содержимое).hexdigest(),
                              "title": (название or имя)[:МАКС_ИМЯ], "source": "manual"}
    _сохранить(данные)
    return токен


def переименовать(токен: str, название: str) -> None:
    название = (название or "").strip()
    if not название:
        raise ОшибкаСейфа("пустое название")
    данные = _загрузить()
    _запись(данные, токен)["title"] = название[:МАКС_ИМЯ]
    _сохранить(данные)


def сменить_метку(токен: str, метка: str) -> None:
    """Меняется только описание вида данных; токен прежний, чтобы не ломать агентов."""
    if метка not in _МЕТКИ:
        raise ОшибкаСейфа(f"неизвестная метка: {метка}")
    данные = _загрузить()
    _запись(данные, токен)["label"] = метка
    _сохранить(данные)


def заменить(токен: str, секрет: str) -> None:
    """Новое значение под тем же токеном (ключ сменили). Старое не показывается."""
    if not секрет:
        raise ОшибкаСейфа("пустой секрет")
    данные = _загрузить()
    запись = _запись(данные, токен)
    if запись.get("kind") == "file":
        raise ОшибкаСейфа("это файл: загрузите новый файл")
    запись["blob"] = base64.b64encode(_dpapi(секрет.encode("utf-8"), True)).decode("ascii")
    запись["changed"] = int(time.time())
    запись.pop("fp", None)
    _сохранить(данные)


def в_корзину(токен: str) -> None:
    данные = _загрузить()
    _запись(данные, токен)["deleted"] = int(time.time())
    _сохранить(данные)


def восстановить(токен: str) -> None:
    данные = _загрузить()
    _запись(данные, токен).pop("deleted", None)
    _сохранить(данные)


def удалить_навсегда(токен: str) -> None:
    данные = _загрузить()
    if not _запись(данные, токен).get("deleted"):
        raise ОшибкаСейфа("сначала переместите запись в корзину")
    данные["items"].pop(токен)
    _сохранить(данные)


def _очистить_корзину(данные) -> bool:
    срок = int(time.time()) - КОРЗИНА_ДНЕЙ * 86400
    старые = [т for т, з in данные["items"].items() if з.get("deleted") and з["deleted"] < срок]
    for т in старые:
        данные["items"].pop(т)
    return bool(старые)


LABELS_EN = {"PII": "ПДн", "Financial": "Финансы", "Health": "Здоровье",
             "Credentials": "УчетныеДанные", "Location": "Локация"}


def положить_json():
    """Для интеграций: JSON {"secret": "...", "label": "Credentials"|"УчетныеДанные"} в stdin.

    Секрет передаётся только через stdin (не через аргументы процесса, не в лог).
    Ответ: {"status": "ok", "token": ..., "label": ...} или {"status": "error", "message": ...}.
    """
    try:
        данные = json.loads(sys.stdin.read() or "{}")
        метка = LABELS_EN.get(данные.get("label", ""), данные.get("label", ""))
        токен = положить(str(данные.get("secret", "")), метка)
        return {"status": "ok", "token": токен, "label": данные.get("label")}
    except ОшибкаСейфа as e:
        return {"status": "error", "message": str(e)}
    except (ValueError, TypeError):
        return {"status": "error", "message": "bad request"}


def _папка_загрузок() -> Path:
    if os.name == "nt":
        try:   # настоящая папка «Загрузки», даже если её перенесли на другой диск
            import ctypes
            import uuid
            g = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID("374DE290-123F-4565-9164-39C4925E467B").bytes_le)
            буф = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(буф)) == 0:
                путь = Path(буф.value)
                ctypes.windll.ole32.CoTaskMemFree(буф)
                return путь
        except Exception:
            pass
    return Path.home() / "Downloads"


def сохранить_файл(токен: str, папка=None) -> str:
    """Расшифровать файл и записать копию в «Загрузки» — только по явной команде пользователя.
    Содержимое не уходит по HTTP: файл пишется на диск этого ПК, выдача пишется в журнал."""
    данные = _загрузить()
    запись = _запись(данные, токен)
    if запись.get("kind") != "file":
        raise ОшибкаСейфа("это не файл")
    содержимое = _dpapi(base64.b64decode(запись["blob"]), False)
    куда = Path(папка) if папка else _папка_загрузок()
    куда.mkdir(parents=True, exist_ok=True)
    имя = _имя_файла(запись.get("filename", "file"))
    стем, суф = os.path.splitext(имя)
    цель, n = куда / имя, 1
    while цель.exists():
        цель, n = куда / f"{стем} ({n}){суф}", n + 1
    with open(цель, "xb") as f:          # x: никогда не перезаписываем существующий файл
        f.write(содержимое)
    данные["audit"].append({"token": токен, "at": int(time.time()), "reason": "saved to disk by the user"})
    _сохранить(данные)
    return str(цель)


def операция_json() -> dict:
    """Для интеграций: JSON {"op": ..., "token": ..., ...} в stdin. Значения секретов не возвращает."""
    try:
        з = json.loads(sys.stdin.read() or "{}")
        op, токен = з.get("op"), str(з.get("token", ""))
        метка = LABELS_EN.get(з.get("label", ""), з.get("label", ""))
        if op == "file":
            содержимое = base64.b64decode(str(з.get("data", "")), validate=True)
            return {"status": "ok", "token": положить_файл(содержимое, str(з.get("filename", "")), метка,
                                                           str(з.get("title", "")))}
        if op == "save":
            return {"status": "ok", "path": сохранить_файл(токен)}
        действия = {"rename": lambda: переименовать(токен, str(з.get("title", ""))),
                    "relabel": lambda: сменить_метку(токен, метка),
                    "replace": lambda: заменить(токен, str(з.get("secret", ""))),
                    "trash": lambda: в_корзину(токен), "restore": lambda: восстановить(токен),
                    "purge": lambda: удалить_навсегда(токен)}
        if op not in действия:
            return {"status": "error", "message": "unknown operation"}
        действия[op]()
        return {"status": "ok"}
    except ОшибкаСейфа as e:
        return {"status": "error", "message": str(e)}
    except (ValueError, TypeError, OSError):
        return {"status": "error", "message": "bad request"}


def main(argv=None):
    import argparse
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["put-json"]:
        результат = положить_json()
        print(json.dumps(результат, ensure_ascii=False))
        return 0 if результат["status"] == "ok" else 3
    if args == ["op-json"]:
        результат = операция_json()
        print(json.dumps(результат, ensure_ascii=False))
        return 0 if результат["status"] == "ok" else 3
    if args == ["list-json"]:
        try:
            print(json.dumps({"status": "ok", "items": список(с_корзиной=True)}, ensure_ascii=False))
            return 0
        except (ОшибкаСейфа, ValueError, OSError):
            print(json.dumps({"status": "error", "message": "The vault is not available."}))
            return 3
    p = argparse.ArgumentParser(prog="yadro-guard vault")
    sub = p.add_subparsers(dest="cmd", required=True)
    put = sub.add_parser("put"); put.add_argument("--label", required=True)
    get = sub.add_parser("get"); get.add_argument("token")
    get.add_argument("--i-have-mandate", action="store_true"); get.add_argument("--reason", default="")
    sub.add_parser("list")
    fg = sub.add_parser("forget"); fg.add_argument("token")
    a = p.parse_args(args)
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
