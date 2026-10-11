# -*- coding: utf-8 -*-
"""Самодостаточный HTML-отчёт Yadro Guard (офлайн, без JS и внешних ресурсов).

Все данные пользователя (исходник, сообщения, пути) экранируются через
html.escape: отчёт инструмента безопасности не должен быть XSS-вектором.
"""
import html, re
from datetime import datetime, timezone
from src import этика_v21 as политика

# Человеческие имена меток: (ярлык, иконка, цвет, пояснение)
МЕТКИ_ЛЮДЯМ = {
    "ПДн": ("Персональные данные", "👤", "#e0533d", "Имена, телефоны, адреса, email — под защитой GDPR и швейц. nFADP."),
    "Финансы": ("Финансовые данные", "💳", "#e8a33d", "Карты, счета, транзакции — под защитой PCI DSS."),
    "Здоровье": ("Медицинские данные", "🏥", "#d14fa0", "Диагнозы и истории болезни — особая категория по GDPR, HIPAA."),
    "УчетныеДанные": ("Учётные данные и ключи", "🔑", "#8a5cf6", "Пароли, токены, приватные ключи, секреты окружения."),
    "Локация": ("Геолокация", "📍", "#2f9fd8", "GPS и координаты — позволяют отследить человека."),
}
# Человеческие имена функций-стоков (куда уходят данные)
СТОК_ЛЮДЯМ = {
    "сеть.отправить": "отправку в сеть", "сеть.запрос": "сетевой запрос", "сеть.пост": "отправку в сеть",
    "http.перенаправить": "HTTP-редирект", "апи.вызов": "внешний API-вызов",
    "файл.записать": "запись в файл", "файл.дописать": "запись в файл", "файл.удалить": "удаление файла",
    "бд.записать": "запись в базу", "бд.вставить": "запись в базу", "бд.обновить": "обновление базы",
    "почта.отправить": "отправку письма", "смс.отправить": "отправку SMS",
    "лог.инфо": "журнал (лог)", "лог.ошибка": "журнал (лог)", "консоль.лог": "вывод в консоль",
    "печать": "вывод программы (печать)",
}
# Человеческие имена санитайзеров (как легально «запечатать» данные перед отправкой)
САНИТАЙЗЕР_ЛЮДЯМ = {
    "зашифровать": "зашифровать", "токенизировать": "заменить на токен", "хэш": "захэшировать",
    "маска": "замаскировать (****)", "анонимизировать": "обезличить",
    "псевдонимизировать": "псевдонимизировать", "редактировать": "вырезать чувствительные части",
    "проверить_согласие": "проверить согласие субъекта", "агрегировать": "агрегировать до статистики",
}
ПОЯСНЕНИЕ = {
    "ЯДРО-Э2301": "Чувствительные данные уходят наружу «как есть» — без защитной обработки.",
    "ЯДРО-Э2302": "Скрытая утечка: сам факт отправки зависит от секрета, по нему можно его вычислить.",
    "ЯДРО-Э2303": "Данные утекают через аргумент вспомогательной функции.",
    "ЯДРО-Э2201": "Функция обращается наружу, не получив на это разрешения (мандата).",
    "ЯДРО-Э2202": "Функция вызывает другую, не унаследовав её разрешения.",
    "ЯДРО-Э2101": "Попытка подменить встроенное правило безопасности.",
}


def человек_метка(м):
    return МЕТКИ_ЛЮДЯМ.get(м, (м, "⚠", "#666", ""))


def человек_сток(имя):
    return СТОК_ЛЮДЯМ.get(имя, имя)


def как_исправить(метки):
    """Для каждой метки — какие обёртки разрешены (из КОМПЛАЕНС). Это и есть «карантин»."""
    планы = []
    for м in метки:
        разрешённые = sorted(политика.КОМПЛАЕНС.get(м, set()))
        ярлык = человек_метка(м)[0]
        варианты = [САНИТАЙЗЕР_ЛЮДЯМ.get(с, с) + f" — <code>{_e(с)}(...)</code>" for с in разрешённые]
        планы.append((ярлык, варианты))
    return планы
СТИЛЬ = """
*{box-sizing:border-box}
body{margin:0;font:15px/1.6 system-ui,Segoe UI,sans-serif;color:#e8ebf2;
 background:radial-gradient(1200px 600px at 80% -10%,#1b2336 0,#0b0e14 60%)}
.wrap{max-width:1000px;margin:0 auto;padding:30px 28px 60px}
header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
.brand{font-weight:800;letter-spacing:.4px;font-size:18px;display:flex;align-items:center;gap:9px}
.brand .dot{width:11px;height:11px;border-radius:50%;box-shadow:0 0 12px currentColor}
.meta{color:#7f8aa3;font-size:12.5px;text-align:right}
.hero{border-radius:16px;padding:22px 26px;display:flex;align-items:center;gap:18px;
 border:1px solid;backdrop-filter:blur(4px)}
.hero .ic{font-size:40px;line-height:1}
.hero h1{margin:0;font-size:26px;letter-spacing:.3px}.hero .sub{margin:3px 0 0;font-size:14px;opacity:.85}
.hero .tag{margin-left:auto;font:600 12px/1 ui-monospace,Consolas;padding:7px 11px;border-radius:8px;background:rgba(255,255,255,.07)}
.bad{background:linear-gradient(90deg,rgba(224,83,61,.18),rgba(224,83,61,.03));border-color:#e0533d;color:#ff9c8c}
.ok{background:linear-gradient(90deg,rgba(62,196,109,.16),rgba(62,196,109,.03));border-color:#3ec46d;color:#8ff0b0}
h2{font-size:12.5px;text-transform:uppercase;letter-spacing:1.4px;color:#7f8aa3;margin:30px 0 12px;font-weight:700}
.card{background:#11151f;border:1px solid #222a3a;border-radius:13px;padding:16px 18px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;border-radius:999px;
 font-size:13px;font-weight:600;color:#fff;margin:0 8px 8px 0;border:1px solid rgba(255,255,255,.18)}
.chip small{font-weight:500;opacity:.9}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:0}
.node{background:#141a26;border:1px solid #2a3344;border-radius:12px;padding:12px 15px;min-width:150px}
.node .lbl{font-size:11px;letter-spacing:.5px;text-transform:uppercase;color:#7f8aa3}
.node b{display:block;color:#fff;font:600 15px/1.4 ui-monospace,Consolas;margin:3px 0 6px}
.node.src{border-color:#8a5cf6}.node.sink{border-color:#e0533d;background:#1d1317}
.arrow{align-self:center;color:#e0533d;font-size:24px;padding:0 10px;font-weight:700}
.fix{display:grid;gap:10px}
.fix .row{display:flex;gap:12px;align-items:flex-start;padding:11px 14px;border-radius:10px;
 background:#101722;border:1px solid #1f3328}
.fix .row .k{font-weight:700;min-width:170px;color:#8ff0b0}
.fix ul{margin:4px 0 0;padding-left:18px}.fix li{margin:2px 0}
code{font-family:ui-monospace,Consolas,monospace;background:rgba(255,255,255,.06);padding:1px 6px;border-radius:5px;font-size:13px}
.msg{background:#0c1119;border:1px solid #1d2432;padding:13px 15px;border-radius:10px;white-space:pre-wrap;color:#c3c9d6;font-size:13.5px}
.code{width:100%;border-collapse:collapse;background:#0c1119;border:1px solid #1d2432;border-radius:10px;overflow:hidden;font:13px/1.7 ui-monospace,Consolas,monospace}
.code td{padding:1px 12px;white-space:pre}.code .n{color:#4a536b;text-align:right;width:1%;user-select:none;border-right:1px solid #1d2432}
.code tr.hit{background:rgba(224,83,61,.18);box-shadow:inset 3px 0 #e0533d}
.code tr.src{background:rgba(138,92,246,.14);box-shadow:inset 3px 0 #8a5cf6}
footer{margin-top:40px;display:flex;gap:8px;align-items:center;color:#566079;font-size:12px}
footer .lock{color:#3ec46d}
.diff{font:13px/1.8 ui-monospace,Consolas,monospace;padding:4px 12px;border-radius:7px;margin:6px 0}
.diff .mark{display:inline-block;width:16px;font-weight:700}
.diff.old{background:rgba(224,83,61,.12);color:#ff9c8c}.diff.old .mark{color:#e0533d}
.diff.new{background:rgba(62,196,109,.12);color:#8ff0b0}.diff.new .mark{color:#3ec46d}
.ok-badge{color:#8ff0b0;font-weight:600;font-size:12.5px}.warn-badge{color:#e8a33d;font-weight:600;font-size:12.5px}
.hint{color:#7f8aa3;font-size:13px;margin:10px 0 0}
"""
_e = lambda т: html.escape(str(т), quote=True)



def _метки(текст):
    return sorted(м for м in политика.ВСЕ_МЕТКИ if re.search(rf"(?<!\w){re.escape(м)}(?!\w)", текст))


def _источники(строки, метки):
    """Строки, где вызываются источники с найденными метками (вероятный старт пути)."""
    найдено = []
    for номер, строка in enumerate(строки, 1):
        for имя, метка in политика.ИСТОЧНИКИ.items():
            if (not метки or метка in метки) and re.search(rf"(?<![\w.]){re.escape(имя)}\s*\(", строка):
                найдено.append((номер, имя, метка))
    return найдено


def _чип(метка):
    ярлык, иконка, цвет, _ = человек_метка(метка)
    return f'<span class="chip" style="background:{цвет}">{иконка} {_e(ярлык)}</span>'


def _карточки_меток(метки):
    ряды = []
    for м in метки:
        ярлык, иконка, цвет, пояснение = человек_метка(м)
        ряды.append(f'<span class="chip" style="background:{цвет}">{иконка} {_e(ярлык)}'
                    f'<small>· {_e(пояснение)}</small></span>')
    return "".join(ряды)


def _карантин(метки):
    """Блок «Как исправить»: допустимые обёртки для каждой метки."""
    строки = []
    for ярлык, варианты in как_исправить(метки):
        пункты = "".join(f"<li>{в}</li>" for в in варианты) or "<li>нет разрешённой обёртки — данные нельзя отправлять наружу</li>"
        строки.append(f'<div class="row"><div class="k">{_e(ярлык)}</div><div><ul>{пункты}</ul></div></div>')
    return f'<div class="fix">{"".join(строки)}</div>'


def _код(строки, выделить, строки_источников):
    ряды = []
    for номер, строка in enumerate(строки, 1):
        класс = "hit" if номер == выделить else "src" if номер in строки_источников else ""
        ряды.append(f'<tr class="{класс}"><td class="n">{номер}</td><td>{_e(строка) or " "}</td></tr>')
    return "<table class='code'>" + "".join(ряды) + "</table>"


def _узел(класс, метка_сверху, имя, низ):
    return (f'<div class="node {класс}"><div class="lbl">{_e(метка_сверху)}</div>'
            f'<b>{_e(имя)}</b>{низ}</div>')


def _diff_строки(было, стало):
    общий = 0
    while общий < len(было) and общий < len(стало) and было[общий] == стало[общий]:
        общий += 1
    return (f'<div class="diff old"><span class="mark">−</span><code>{_e(было)}</code></div>'
            f'<div class="diff new"><span class="mark">+</span><code>{_e(стало)}</code></div>')


def _автофикс_блок(диагностика):
    try:
        from src import autofix
        план = autofix.предложить(диагностика.get("_исходник", ""), диагностика)
    except Exception:
        план = None
    if not план:
        return ""
    статус = ('<span class="ok-badge">✓ проверено: исправленный код проходит анализатор</span>'
              if план["проверено"] else
              '<span class="warn-badge">⚠ требует ручной проверки</span>')
    return (f'<h2>🪄 Автоисправление — было / стало</h2>'
            f'<div class="card"><p>Обернуть аргумент в <code>{_e(план["обёртка"])}(...)</code> '
            f'на строке {план["строка"]}. {статус}</p>'
            f'{_diff_строки(план["было"], план["стало"])}'
            f'<p class="hint">Применить автоматически: '
            f'<code>yadro-guard scan файл --fix</code></p></div>')


def _нарушение(строки, диагностика):
    сообщение, код, строка = диагностика["message"], диагностика["code"], диагностика["line"]
    метки = _метки(сообщение)
    сток = re.search(r"стока? '([^']+)'", сообщение) or re.search(r"вызывает '([^']+)'", сообщение)
    сток = сток.group(1) if сток else "?"
    истоки = _источники(строки, set(метки))
    узлы = [_узел("src", f"строка {н}", f"{и}()", _чип(м)) for н, и, м in истоки[:4]]
    if not узлы:
        узлы = [_узел("src", "источник", "чувствительные данные", "")]
    узлы.append(_узел("sink", f"строка {строка} · утечка", сток, f"<span class='lbl'>{_e(человек_сток(сток))}</span>"))
    поток = '<div class="arrow">→</div>'.join(узлы)
    hero = (f'<div class="hero bad"><div class="ic">⛔</div><div>'
            f'<h1>Обнаружена утечка</h1>'
            f'<div class="sub">{_e(ПОЯСНЕНИЕ.get(код, "Нарушение политики потоков данных."))}</div>'
            f'</div><div class="tag">{_e(код)}</div></div>')
    тело = (f'<h2>Что утекает</h2><div>{_карточки_меток(метки)}</div>'
            f'<h2>Путь данных</h2><div class="flow">{поток}</div>'
            f'<h2>🛡 Карантин — как отправить легально</h2>'
            f'<div class="card">Если эти данные действительно нужно передать наружу, '
            f'сначала «запечатайте» их одной из разрешённых обёрток:{_карантин(метки)}</div>'
            f'{_автофикс_блок(диагностика)}'
            f'<h2>Техническое сообщение</h2><pre class="msg">{_e(сообщение)}</pre>'
            f'<h2>Исходный код</h2>{_код(строки, строка, {н for н, _, _ in истоки})}')
    return hero, тело


def _чисто(строки, находки):
    hero = ('<div class="hero ok"><div class="ic">✅</div><div>'
            '<h1>Утечек не найдено</h1>'
            '<div class="sub">Все чувствительные данные обработаны или не покидают программу.</div>'
            '</div><div class="tag">OK</div></div>')
    санитайзы = [з for з in (находки or []) if getattr(з, "статус", "") == "САНИТАЙЗ"]
    список = "".join(f'<div class="row"><div class="k">{_чип(з.метка)}</div>'
                     f'<div>строка {з.строка}: обёртка <code>{_e(з.источник)}(...)</code> сняла метку</div></div>'
                     for з in санитайзы)
    тело = ((f'<h2>Применённые обёртки</h2><div class="fix">{список}</div>' if список else "")
            + f"<h2>Исходный код</h2>{_код(строки, 0, set())}")
    return hero, тело


def построить(путь, исходник, диагностика=None, находки=None, версия=""):
    """диагностика: dict из guard_impl.diagnostic, или None, если нарушений нет."""
    строки = исходник.splitlines()
    плохо = bool(диагностика)
    hero, тело = _нарушение(строки, диагностика) if плохо else _чисто(строки, находки)
    цвет_точки = "#e0533d" if плохо else "#3ec46d"
    время = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>Yadro Guard — отчёт</title><style>{СТИЛЬ}</style></head><body><div class=\"wrap\">"
            f'<header><span class="brand"><span class="dot" style="color:{цвет_точки}"></span>YADRO GUARD</span>'
            f'<span class="meta">{_e(путь)}<br>{время} · v{_e(версия)}</span></header>'
            f'{hero}{тело}'
            f'<footer><span class="lock">🔒</span> Отчёт создан локально. Данные никуда не отправлялись.</footer>'
            "</div></body></html>")
