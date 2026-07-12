import unittest
from llvmlite import binding as llvm
from src.main import компилировать,ОшибкаСемантики,ОшибкаCheckedАрифметики
from src.кодоген import Кодоген,ОшибкаКодогена
class ТестыCheckedArithmetic(unittest.TestCase):
 def verified(self,source,profile="checked"):
  text=компилировать(source,арифметика=profile);module=llvm.parse_assembly(text);module.verify();return text
 def test_default_semantics_unchanged(self):
  text=self.verified("функ старт() { вернуть 9223372036854775807 + 1 }","default")
  self.assertNotIn("with.overflow",text);self.assertNotIn("llvm.trap",text)
 def test_checked_intrinsics(self):
  for op,name in (("+","sadd"),("-","ssub"),("*","smul")):
   text=self.verified(f"функ calc(x) {{ вернуть x {op} 2 }} функ старт() {{ вернуть calc(3) }}")
   self.assertIn(f"llvm.{name}.with.overflow.i64",text);self.assertIn("yadro_checked_trap",text);self.assertIn("call void @\"llvm.trap\"()",text);self.assertIn("unreachable",text)
 def test_checked_div_guards_precede_sdiv(self):
  text=self.verified("функ calc(x, y) { вернуть x / y } функ старт() { вернуть calc(8, 2) }")
  self.assertIn("div.zero",text);self.assertIn("div.minimum",text);self.assertIn("div.minus_one",text);self.assertLess(text.index("div.invalid"),text.index("sdiv i64"))
 def test_profile_state_is_instance_local(self):
  source="функ calc(x) { вернуть x + 1 } функция старт() { вернуть calc(1) }".replace("функция","функ");first=компилировать(source);checked=компилировать(source,арифметика="checked");last=компилировать(source)
  self.assertNotIn("with.overflow",first);self.assertIn("sadd.with.overflow",checked);self.assertNotIn("with.overflow",last)
  self.assertEqual("default",Кодоген().arithmetic_profile);self.assertEqual("checked",Кодоген(arithmetic_profile="checked").arithmetic_profile)
 def test_invalid_profile_fails_closed(self):
  source="функ старт() { вернуть 0 }"
  for profile in ("fast-magic",None,True,[]):
   with self.subTest(profile=repr(profile)),self.assertRaisesRegex(ОшибкаСемантики,"Неизвестный arithmetic profile"):компилировать(source,арифметика=profile)
   with self.subTest(direct=repr(profile)),self.assertRaisesRegex(ОшибкаКодогена,"неизвестный arithmetic profile"):Кодоген(arithmetic_profile=profile)
 def test_checked_constant_overflow_rejected_only_in_checked(self):
  cases=("9223372036854775807 + 1","((0 - 9223372036854775807) - 1) - 1","9223372036854775807 * 2")
  for expression in cases:
   source=f"функ старт() {{ вернуть {expression} }}";компилировать(source)
   with self.subTest(expression=expression),self.assertRaises(ОшибкаCheckedАрифметики) as caught:компилировать(source,арифметика="checked")
   self.assertEqual("ЯДРО-А1001",caught.exception.код);self.assertIn("строка 1",str(caught.exception))
 def test_boundaries(self):
  self.verified("функ старт() { вернуть 9223372036854775807 + 0 }");self.verified("функ старт() { вернуть (0 - 9223372036854775807) - 1 }")
if __name__=="__main__":unittest.main()
