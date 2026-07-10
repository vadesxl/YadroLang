import unittest
from src.main import компилировать
from src.типы import ОшибкаТипов
class ТестыПутейВозврата(unittest.TestCase):
 def test_helper_missing_return(self):
  with self.assertRaisesRegex(ОшибкаТипов,"ЯДРО-Т2204"):компилировать("функ helper(x) { если x > 0 { вернуть 1 } } функ старт() { вернуть helper(1) }")
 def test_entry_implicit_zero(self):компилировать("функ старт() { печать(1) }")
 def test_both_branches(self):компилировать("функ helper(x) { если x > 0 { вернуть 1 } иначе { вернуть 0 } } функ старт() { вернуть helper(1) }")
if __name__=="__main__":unittest.main()
