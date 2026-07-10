import unittest
from llvmlite import binding as llvm
from src.лексер import Лексер
from src.синтаксис import Парсер
from src.типы import ПроверкаТипов,ОшибкаТипов,БУЛЕВ
from src.main import СИСТЕМНЫЕ_API
from src.кодоген import Кодоген
class ТестыТипов(unittest.TestCase):
 def проверить(self,код):
  ast=Парсер(Лексер(код).токены()).разобрать();return ast,ПроверкаТипов(ast,СИСТЕМНЫЕ_API).проверить()
 def test_сравнение_bool_и_valid_ir(self):
  ast,типы=self.проверить("функ старт() { вернуть 1 < 2 }");self.assertEqual(БУЛЕВ,типы.возвраты["старт"]);llvm.parse_assembly(Кодоген().сгенерировать(ast)).verify()
 def test_смешанная_арифметика(self):
  with self.assertRaisesRegex(ОшибкаТипов,"ЯДРО-Т2301"):self.проверить('функ старт() { вернуть "x" + 1 }')
 def test_строковая_переменная(self):
  with self.assertRaisesRegex(ОшибкаТипов,"ЯДРО-Т2305"):self.проверить('функ старт() { пусть x = "привет" вернуть 0 }')
 def test_недостижимое(self):
  with self.assertRaisesRegex(ОшибкаТипов,"ЯДРО-Т2202"):self.проверить("функ старт() { вернуть 1 печать(2) }")
 def test_не_все_пути(self):
  with self.assertRaisesRegex(ОшибкаТипов,"ЯДРО-Т2204"):self.проверить("функ старт() { если 1 < 2 { вернуть 1 } }")
 def test_обе_ветки_return(self):
  ast,_=self.проверить("функ старт() { если 1 < 2 { вернуть 1 } иначе { вернуть 2 } }");llvm.parse_assembly(Кодоген().сгенерировать(ast)).verify()
 def test_печать_строки(self):
  ast,_=self.проверить('функ старт() { печать("привет") вернуть 0 }');llvm.parse_assembly(Кодоген().сгенерировать(ast)).verify()
if __name__=="__main__":unittest.main()
