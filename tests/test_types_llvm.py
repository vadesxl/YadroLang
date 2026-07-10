import unittest
from llvmlite import binding as llvm
from src.main import компилировать
from src.типы import ОшибкаТипов
class ТестыТиповLLVM(unittest.TestCase):
 def verified(self,код):т=компилировать(код);м=llvm.parse_assembly(т);м.verify();return т
 def test_bool_и_сравнение(self):self.verified("функ старт() { пусть х = истина если х { вернуть 1 } иначе { вернуть 0 } }");self.verified("функ старт() { если 2 > 1 { вернуть 1 } вернуть 0 }")
 def test_печать_строки(self):self.verified('функ старт() { печать("привет") вернуть 0 }')
 def test_смешанная_арифметика(self):
  with self.assertRaisesRegex(ОшибкаТипов,"требует i64"):компилировать("функ старт() { вернуть истина + 1 }")
 def test_строка_как_условие(self):
  with self.assertRaisesRegex(ОшибкаТипов,"условие"):компилировать('функ старт() { если "x" { вернуть 1 } вернуть 0 }')
 def test_разные_возвраты(self):
  with self.assertRaisesRegex(ОшибкаТипов,"тип возврата"):компилировать('функ старт() { если истина { вернуть 1 } иначе { вернуть "x" } }')
 def test_недостижимое(self):
  with self.assertRaisesRegex(ОшибкаТипов,"недостижимое"):компилировать("функ старт() { вернуть 1 печать(2) }")
 def test_nested_и_recursion(self):self.verified("функ id(x) { вернуть x } функ twice(x) { вернуть id(id(x)) } функ старт() { вернуть twice(2) }");self.verified("функ down(x) { если x > 0 { вернуть down(x - 1) } вернуть 0 } функ старт() { вернуть down(3) }")
if __name__=="__main__":unittest.main()
