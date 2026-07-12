# -*- coding: utf-8 -*-
"""Canonical typed LLVM backend selected after branch differential audit."""
from src import кодоген_verified as _backend
from src.abi import symbol
from src.типы_sound import ЗвуковаяПроверкаТипов
from src.этика import ИСТОЧНИКИ,СТОКИ,САНИТАЙЗЕРЫ
ОшибкаКодогена=_backend.ОшибкаКодогена
class Кодоген(_backend.Кодоген):
 def __init__(self,arithmetic_profile="default"):
  if not isinstance(arithmetic_profile,str) or arithmetic_profile not in {"default","checked"}:raise ОшибкаКодогена("неизвестный arithmetic profile")
  super().__init__(symbol_mangler=symbol,arithmetic_profile=arithmetic_profile)
 def сгенерировать(self,программа):
  ЗвуковаяПроверкаТипов(set(ИСТОЧНИКИ)|set(СТОКИ)|set(САНИТАЙЗЕРЫ)|{"печать"}).проверить(программа)
  return super().сгенерировать(программа)
