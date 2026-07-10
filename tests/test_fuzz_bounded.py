import random
import string
import unittest
from src.лексер import Лексер,ОшибкаЛексера
from src.синтаксис import Парсер,ОшибкаПарсера
class ТестыОграниченногоFuzz(unittest.TestCase):
 def test_deterministic_lexer(self):
  rng=random.Random(20260710);алфавит=string.ascii_letters+string.digits+' _#\n{}()[],+-*/<>=\".Жя'
  for _ in range(300):
   текст=''.join(rng.choice(алфавит) for _ in range(rng.randrange(0,160)))
   try:Лексер(текст).токены()
   except (ОшибкаЛексера,ValueError,IndexError):pass
 def test_parser_progress(self):
  for текст in ['функ старт( {','функ старт() {','функ старт() { вернуть (1 + 2 }','функ старт() { пусть х = "','функ '*200]:
   try:Парсер(Лексер(текст).токены()).разобрать()
   except (ОшибкаЛексера,ОшибкаПарсера,ValueError,IndexError,RecursionError):pass
if __name__=='__main__':unittest.main()
