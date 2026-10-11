# -*- coding: utf-8 -*-
"""Стабильный фасад Yadro Guard CLI."""
from src import guard_impl as _impl
_исходная_классификация = _impl.классифицировать
def _классифицировать_с_типами(ошибка):
    if ошибка.__class__.__name__ == "ОшибкаТипов":
        return _impl.ОШИБКА_ИСХОДНИКА
    return _исходная_классификация(ошибка)
_impl.классифицировать = _классифицировать_с_типами
from src.guard_impl import *  # noqa: F401,F403,E402

if __name__ == "__main__":
    # Без этого `python -m src.guard ...` молча завершался с кодом 0,
    # и CI-гейт "проходил", не выполнив проверку (fail-open).
    main()
