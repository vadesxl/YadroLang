import unittest
from llvmlite import binding as llvm
from src.main import компилировать
from src.типы import ОшибкаТипов
class ТестыТиповLLVM(unittest.TestCase):
 def verified(self,код):т=компилировать(код);м=llvm.parse_assembly(т);м.verify();return т
 def test_bool(self):self.verified("функ старт() { пусть х = истина если х { вернуть 1 } иначе { вернуть 0 } }")
 def test_string(self):self.verified('функ старт() { печать("привет") вернуть 0 }')
 def test_mixed(self):
  with self.assertRaisesRegex(ОшибкаТипов,"требует i64"):компилировать("функ старт() { вернуть истина + 1 }")
 def test_condition(self):
  with self.assertRaisesRegex(ОшибкаТипов,"условие"):компилировать('функ старт() { если "x" { вернуть 1 } вернуть 0 }')
 def test_returns(self):
  with self.assertRaisesRegex(ОшибкаТипов,"тип возврата"):компилировать('функ старт() { если истина { вернуть 1 } иначе { вернуть "x" } }')
 def test_unreachable(self):
  with self.assertRaisesRegex(ОшибкаТипов,"недостижимое"):компилировать("функ старт() { вернуть 1 печать(2) }")
 def test_recursion(self):self.verified("функ down(x) { если x > 0 { вернуть down(x - 1) } вернуть 0 } функ старт() { вернуть down(3) }")
if __name__=="__main__":unittest.main()
