# -*- coding: utf-8 -*-
"""Самодостаточный HTML-отчёт Yadro Guard (офлайн, без JS и внешних ресурсов).

Все данные пользователя (исходник, сообщения, пути) экранируются через
html.escape: отчёт инструмента безопасности не должен быть XSS-вектором.
"""
import html, re
from datetime import datetime, timezone
from src import этика_v21 as политика

ЦВЕТА = {"ПДн": "#e0533d", "Финансы": "#e8a33d", "Здоровье": "#d14fa0",
         "УчетныеДанные": "#8a5cf6", "Локация": "#2f9fd8"}
ПОЯСНЕНИЕ = {
    "ЯДРО-Э2301": "Чувствительные данные напрямую попадают в сток без подходящего санитайзера.",
    "ЯДРО-Э2302": "Неявный поток: решение о вызове стока зависит от секретных данных.",
    "ЯДРО-Э2303": "Данные утекают через параметр вспомогательной функции.",
    "ЯДРО-Э2201": "Функция вызывает сток, не объявив нужный мандат.",
    "ЯДРО-Э2202": "Функция вызывает другую, не объявив её мандаты.",
    "ЯДРО-Э2101": "Попытка подменить зарезервированный символ политики.",
}
СТИЛЬ = """
body{margin:0;font:15px/1.5 system-ui,Segoe UI,sans-serif;background:#0f1218;color:#e6e9ef}
.wrap{max-width:980px;margin:0 auto;padding:28px}
header{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #262c38;padding-bottom:12px}
.brand{font-weight:700;letter-spacing:.5px}.meta{color:#8b93a7;font-size:13px}
.verdict{margin:22px 0 8px;padding:18px 22px;border-radius:12px;font-size:24px;font-weight:700}
.verdict small{font-size:14px;opacity:.8;margin-left:8px}
.bad{background:#3a1418;border:1px solid #e0533d}.ok{background:#12301f;border:1px solid #3ec46d}
.why{color:#c3c9d6}h2{font-size:15px;text-transform:uppercase;letter-spacing:1px;color:#8b93a7;margin-top:28px}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;color:#fff;font-size:12px;font-weight:600;margin:0 6px 4px 0}
.flow{display:flex;flex-wrap:wrap;align-items:center;gap:8px}
.node{background:#1a1f2a;border:1px solid #2d3445;border-radius:10px;padding:10px 14px;font-size:12px;color:#8b93a7}
.node b{display:block;color:#e6e9ef;font-size:14px;font-family:Consolas,monospace}
.node.sink{border-color:#e0533d}.node.src{border-color:#8a5cf6}.arrow{color:#e0533d;font-size:22px}
.msg{background:#1a1f2a;padding:12px;border-radius:8px;white-space:pre-wrap}
.code{width:100%;border-collapse:collapse;background:#151922;font:13px Consolas,monospace}
.code td{padding:1px 10px;white-space:pre}.code .n{color:#59617a;text-align:right;width:1%}
.code tr.hit{background:#4a1a1f}.code tr.src{background:#2a2145}
footer{margin-top:36px;color:#59617a;font-size:12px}
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
    return f'<span class="chip" style="background:{ЦВЕТА.get(метка, "#666")}">{_e(метка)}</span>'


def _код(строки, выделить, строки_источников):
    ряды = []
    for номер, строка in enumerate(строки, 1):
        класс = "hit" if номер == выделить else "src" if номер in строки_источников else ""
        ряды.append(f'<tr class="{класс}"><td class="n">{номер}</td><td>{_e(строка) or " "}</td></tr>')
    return "<table class='code'>" + "".join(ряды) + "</table>"


def _нарушение(строки, диагностика):
    сообщение, код, строка = диагностика["message"], диагностика["code"], диагностика["line"]
    метки = _метки(сообщение)
    сток = re.search(r"стока? '([^']+)'", сообщение) or re.search(r"вызывает '([^']+)'", сообщение)
    сток = сток.group(1) if сток else "?"
    истоки = _источники(строки, set(метки))
    этапы = "".join(f'<div class="node src">строка {н}<b>{_e(и)}()</b>{_чип(м)}</div><div class="arrow">→</div>'
                    for н, и, м in истоки[:4])
    if not этапы:
        этапы = '<div class="node src">источник<b>чувствительные данные</b></div><div class="arrow">→</div>'
    статус = f'<div class="verdict bad">⛔ ЗАБЛОКИРОВАНО <small>{_e(код)}</small></div>'
    тело = (f'<p class="why">{_e(ПОЯСНЕНИЕ.get(код, "Нарушение политики потоков данных."))}</p>'
            f'<div>{"".join(_чип(м) for м in метки)}</div>'
            f'<h2>Путь утечки</h2><div class="flow">{этапы}'
            f'<div class="node sink">строка {строка}<b>{_e(сток)}</b>сток</div></div>'
            f'<h2>Сообщение анализатора</h2><pre class="msg">{_e(сообщение)}</pre>'
            f'<h2>Исходный код</h2>{_код(строки, строка, {н for н, _, _ in истоки})}')
    return статус, тело


def _чисто(строки, находки):
    статус = '<div class="verdict ok">✅ УТЕЧЕК НЕ НАЙДЕНО</div>'
    санитайзы = [з for з in (находки or []) if getattr(з, "статус", "") == "САНИТАЙЗ"]
    список = "".join(f"<li>строка {з.строка}: {_чип(з.метка)} снята санитайзером <b>{_e(з.источник)}</b></li>"
                     for з in санитайзы)
    тело = ('<p class="why">Все потоки чувствительных данных прошли разрешённые санитайзеры.</p>'
            + (f"<h2>Деклассификации</h2><ul>{список}</ul>" if список else "")
            + f"<h2>Исходный код</h2>{_код(строки, 0, set())}")
    return статус, тело


def построить(путь, исходник, диагностика=None, находки=None, версия=""):
    """диагностика: dict из guard_impl.diagnostic, или None, если нарушений нет."""
    строки = исходник.splitlines()
    статус, тело = _нарушение(строки, диагностика) if диагностика else _чисто(строки, находки)
    время = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>Yadro Guard — отчёт</title><style>{СТИЛЬ}</style></head><body><div class=\"wrap\">"
            f'<header><span class="brand">🛡 YADRO GUARD</span>'
            f'<span class="meta">{_e(путь)} · {время} · v{_e(версия)}</span></header>'
            f"{статус}{тело}<footer>Отчёт создан локально. Данные никуда не отправлялись.</footer>"
            "</div></body></html>")
