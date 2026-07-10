import unittest
from llvmlite import binding as llvm
from src.main import компилировать
from src.типизация import ОшибкаТипов
class ТестыТиповLLVM(unittest.TestCase):
 def код(self,код,исходник):
  with self.assertRaises(ОшибкаТипов) as ошибка:компилировать(исходник)
  self.assertEqual(код,ошибка.exception.код)
 def test_bool_ir(self):м=llvm.parse_assembly(компилировать("функ старт() { если истина { вернуть 1 } иначе { вернуть 0 } }"));м.verify()
 def test_bool_арифметика(self):self.код("ЯДРО-Т1001","функ старт() { вернуть истина + 1 }")
 def test_строка_в_переменной(self):self.код("ЯДРО-Т1005",'функ старт() { пусть х = "секрет" вернуть 0 }')
 def test_недостижимое(self):self.код("ЯДРО-Т1008","функ старт() { вернуть 1 пусть х = 2 }")
 def test_смешанные_возвраты(self):self.код("ЯДРО-Т1001","функ старт() { если 1 { вернуть истина } вернуть 0 }")
 def test_печать_строки(self):м=llvm.parse_assembly(компилировать('функ старт() { печать("привет") вернуть 0 }'));м.verify()
 def test_bool_возврат_abi(self):м=llvm.parse_assembly(компилировать("функ старт() { вернуть 2 > 1 }"));м.verify()
if __name__=="__main__":unittest.main()
