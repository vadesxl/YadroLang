# -*- coding: utf-8 -*-
from src import кодоген_verified as _backend
from src.abi import symbol
from src.типы_sound import ЗвуковаяПроверкаТипов
from src.этика import ИСТОЧНИКИ,СТОКИ,САНИТАЙЗЕРЫ
ОшибкаКодогена=_backend.ОшибкаКодогена
class Кодоген(_backend.Кодоген):
 def __init__(self):super().__init__(symbol_mangler=symbol)
 def сгенерировать(self,программа):
  ЗвуковаяПроверкаТипов(set(ИСТОЧНИКИ)|set(СТОКИ)|set(САНИТАЙЗЕРЫ)|{"печать"}).проверить(программа)
  return super().сгенерировать(программа)
