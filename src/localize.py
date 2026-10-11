# -*- coding: utf-8 -*-
"""Локализация Yadro Guard: один движок, два языка (ru / en).

Движок работает с каноническими (русскими) именами. Английский исходник
переводится в канонический ПО ТОКЕНАМ: строковые литералы и комментарии не
трогаются, переводов строк не добавляется, поэтому номера строк в
диагностике совпадают с исходником пользователя. Тексты для людей строятся
из структурированных данных, а не переводом русских сообщений.
"""
import re

BRAND = "Yadro Guard"  # переименование продукта = одна строка

KEYWORDS_EN = {"fn": "функ", "let": "пусть", "return": "вернуть", "if": "если",
               "else": "иначе", "while": "пока", "true": "истина", "false": "ложь",
               "requires": "требует", "main": "старт", "print": "печать"}

LABELS_EN = {"ПДн": "PII", "Финансы": "Financial", "Здоровье": "Health",
             "УчетныеДанные": "Credentials", "Локация": "Location"}

CAPS_EN = {"ДоступСети": "NetworkAccess", "ЗаписьДиска": "DiskWrite",
           "ЗаписьБД": "DatabaseWrite", "ЧтениеБД": "DatabaseRead",
           "ДоступЛог": "LogAccess", "ВыводПрограммы": "ProgramOutput"}

API_EN = {
    "сеть.отправить": "net.send", "сеть.запрос": "net.request", "сеть.пост": "net.post",
    "http.перенаправить": "http.redirect", "вс.отправить": "ws.send",
    "файл.записать": "file.write", "файл.удалить": "file.delete", "файл.дописать": "file.append",
    "бд.записать": "db.write", "бд.вставить": "db.insert", "бд.обновить": "db.update",
    "бд.удалить": "db.delete", "бд.запрос": "db.query", "лог.инфо": "log.info",
    "лог.отладка": "log.debug", "лог.ошибка": "log.error", "консоль.лог": "console.log",
    "апи.вызов": "api.call", "почта.отправить": "email.send", "смс.отправить": "sms.send",
    "пользователь.данные": "user.data", "пользователь.имя": "user.name",
    "пользователь.почта": "user.email", "пользователь.телефон": "user.phone",
    "пользователь.адрес": "user.address", "пользователь.ид": "user.id",
    "личные.прочитать": "personal.read", "запрос.тело": "request.body",
    "запрос.параметры": "request.params", "куки.получить": "cookie.get",
    "сессия.получить": "session.get", "платеж.карта": "payment.card",
    "счет.баланс": "account.balance", "транзакция.получить": "transaction.get",
    "банк.счет": "bank.account", "пациент.запись": "patient.record",
    "медицина.история": "medical.history", "диагноз.получить": "diagnosis.get",
    "среда.секрет": "env.secret", "хранилище.прочитать": "vault.read",
    "ключ.приватный": "key.private", "гео.локация": "geo.location",
    "гпс.координаты": "gps.coordinates", "файл.прочитать": "file.read",
    "сеть.принять": "net.accept", "бд.прочитать": "db.read",
    "анонимизировать": "anonymize", "проверить_согласие": "check_consent", "хэш": "hash",
    "зашифровать": "encrypt", "маска": "mask", "редактировать": "redact",
    "токенизировать": "tokenize", "псевдонимизировать": "pseudonymize", "агрегировать": "aggregate",
    "печать": "print",
}

EN_TO_RU = {**{v: k for k, v in API_EN.items()}, **{v: k for k, v in CAPS_EN.items()}, **KEYWORDS_EN}
RU_TO_EN = {**API_EN, **CAPS_EN, **LABELS_EN, **{v: k for k, v in KEYWORDS_EN.items()}}
LABEL_HUMAN = {
    "ПДн": {"ru": ("Персональные данные", "👤", "#e0533d", "Имена, телефоны, адреса, email — GDPR и nFADP."),
            "en": ("Personal data", "👤", "#e0533d", "Names, phones, addresses, emails — protected by GDPR / nFADP.")},
    "Финансы": {"ru": ("Финансовые данные", "💳", "#e8a33d", "Карты, счета, транзакции — PCI DSS."),
                "en": ("Financial data", "💳", "#e8a33d", "Cards, accounts, transactions — protected by PCI DSS.")},
    "Здоровье": {"ru": ("Медицинские данные", "🏥", "#d14fa0", "Диагнозы, истории болезни — особая категория GDPR, HIPAA."),
                 "en": ("Health data", "🏥", "#d14fa0", "Diagnoses and medical records — special category under GDPR / HIPAA.")},
    "УчетныеДанные": {"ru": ("Учётные данные и ключи", "🔑", "#8a5cf6", "Пароли, токены, приватные ключи, секреты окружения."),
                      "en": ("Credentials & keys", "🔑", "#8a5cf6", "Passwords, tokens, private keys, environment secrets.")},
    "Локация": {"ru": ("Геолокация", "📍", "#2f9fd8", "GPS и координаты — позволяют отследить человека."),
                "en": ("Location data", "📍", "#2f9fd8", "GPS coordinates — can be used to track a person.")},
}

SINK_HUMAN = {
    "en": {"net": "sending over the network", "http": "an HTTP redirect", "ws": "a websocket message",
           "file": "writing to a file", "db": "a database operation", "log": "an application log",
           "console": "console output", "api": "an external API call", "email": "sending an email",
           "sms": "sending an SMS", "print": "program output"},
    "ru": {"сеть": "отправку в сеть", "http": "HTTP-редирект", "вс": "websocket-сообщение",
           "файл": "запись в файл", "бд": "операцию с базой", "лог": "журнал (лог)",
           "консоль": "вывод в консоль", "апи": "внешний API-вызов", "почта": "отправку письма",
           "смс": "отправку SMS", "печать": "вывод программы"},
}

SANITIZER_HUMAN = {
    "зашифровать": {"ru": "зашифровать", "en": "encrypt"},
    "токенизировать": {"ru": "заменить на токен", "en": "replace with a token"},
    "хэш": {"ru": "захэшировать", "en": "hash (one-way)"},
    "маска": {"ru": "замаскировать (****)", "en": "mask (****)"},
    "анонимизировать": {"ru": "обезличить", "en": "anonymize"},
    "псевдонимизировать": {"ru": "псевдонимизировать", "en": "pseudonymize"},
    "редактировать": {"ru": "вырезать чувствительные части", "en": "redact sensitive parts"},
    "проверить_согласие": {"ru": "проверить согласие субъекта", "en": "verify the person's consent"},
    "агрегировать": {"ru": "агрегировать до статистики", "en": "aggregate into statistics"},
}

WHY = {
    "ЯДРО-Э2301": {"ru": "Чувствительные данные уходят наружу «как есть» — без защитной обработки.",
                   "en": "Sensitive data leaves the program as-is, without any protective wrapping."},
    "ЯДРО-Э2302": {"ru": "Скрытая утечка: сам факт отправки зависит от секрета, по нему можно его вычислить.",
                   "en": "Hidden leak: whether something is sent depends on a secret, so the secret can be inferred."},
    "ЯДРО-Э2303": {"ru": "Данные утекают через аргумент вспомогательной функции.",
                   "en": "Data leaks through an argument passed to a helper function."},
    "ЯДРО-Э2201": {"ru": "Функция обращается наружу, не получив на это разрешения (мандата).",
                   "en": "A function reaches the outside world without declaring the permission it needs."},
    "ЯДРО-Э2202": {"ru": "Функция вызывает другую, не унаследовав её разрешения.",
                   "en": "A function calls another one without declaring the permissions that one needs."},
    "ЯДРО-Э2101": {"ru": "Попытка подменить встроенное правило безопасности.",
                   "en": "The code tries to redefine a built-in security rule."},
}
WHY_DEFAULT = {"ru": "Нарушение политики потоков данных.", "en": "Data-flow policy violation."}

_TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|#[^\n]*|[^\W\d]\w*(?:\.[^\W\d]\w*)*', re.UNICODE)


def detect_lang(source: str) -> str:
    """ru, если есть русское ключевое слово функции; иначе en."""
    return "ru" if re.search(r"(?<![\w.])функ(?![\w.])", source) else "en"


def to_canonical(source: str) -> str:
    """Английский исходник -> канонический (русский), только по токенам-именам."""
    def заменить(m):
        т = m.group(0)
        if т[0] in '"#':
            return т
        return EN_TO_RU.get(т, т)
    return _TOKEN.sub(заменить, source)


def name_for(canonical_name: str, lang: str) -> str:
    return RU_TO_EN.get(canonical_name, canonical_name) if lang == "en" else canonical_name


def label_info(label_id: str, lang: str) -> dict:
    ярлык, иконка, цвет, пояснение = LABEL_HUMAN.get(label_id, {}).get(lang, (label_id, "⚠", "#666", ""))
    return {"id": LABELS_EN.get(label_id, label_id) if lang == "en" else label_id,
            "label": ярлык, "icon": иконка, "color": цвет, "about": пояснение}


def sink_human(canonical_sink: str, lang: str) -> str:
    имя = name_for(canonical_sink, lang)
    return SINK_HUMAN[lang].get(имя.split(".")[0], имя)


def sanitizer_human(canonical: str, lang: str) -> str:
    return SANITIZER_HUMAN.get(canonical, {}).get(lang, canonical)


def why(code: str, lang: str) -> str:
    return WHY.get(code, WHY_DEFAULT)[lang]
