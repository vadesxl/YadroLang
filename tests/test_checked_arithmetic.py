import unittest
from llvmlite import binding as llvm
from src.main import компилировать,ОшибкаСемантики
class ТестыCheckedArithmetic(unittest.TestCase):
 def verified(self,source,profile="checked"):
  text=компилировать(source,арифметика=profile);module=llvm.parse_assembly(text);module.verify();return text
 def test_default_semantics_unchanged(self):
  text=self.verified("функ старт() { вернуть 9223372036854775807 + 1 }","default")
  self.assertNotIn("with.overflow",text);self.assertNotIn("llvm.trap",text)
 def test_checked_intrinsics(self):
  for op,name in (("+","sadd"),("-","ssub"),("*","smul")):
   text=self.verified(f"функ calc(x) {{ вернуть x {op} 2 }} функ старт() {{ вернуть calc(3) }}")
   self.assertIn(f"llvm.{name}.with.overflow.i64",text);self.assertIn("yadro_checked_trap",text);self.assertIn("unreachable",text)
 def test_checked_div_guards_precede_sdiv(self):
  text=self.verified("функ calc(x, y) { вернуть x / y } функ старт() { вернуть calc(8, 2) }")
  self.assertIn("div.zero",text);self.assertIn("div.minimum",text);self.assertIn("div.minus_one",text);self.assertLess(text.index("div.invalid"),text.index("sdiv i64"))
 def test_profile_state_is_instance_local(self):
  source="функ calc(x) { вернуть x + 1 } функ старт() { вернуть calc(1) }";first=компилировать(source);checked=компилировать(source,арифметика="checked");last=компилировать(source)
  self.assertNotIn("with.overflow",first);self.assertIn("sadd.with.overflow",checked);self.assertNotIn("with.overflow",last)
 def test_invalid_profile_fails_closed(self):
  with self.assertRaisesRegex(ОшибкаСемантики,"Неизвестный arithmetic profile"):компилировать("функ старт() { вернуть 0 }",арифметика="fast-magic")
 def test_checked_constant_overflow_rejected_only_in_checked(self):
  source="функ старт() { вернуть 9223372036854775807 + 1 }";компилировать(source)
  with self.assertRaisesRegex(ОшибкаСемантики,"Переполнение checked i64"):компилировать(source,арифметика="checked")
 def test_boundaries(self):
  self.verified("функ старт() { вернуть 9223372036854775807 + 0 }");self.verified("функ старт() { вернуть (0 - 9223372036854775807) - 1 }")
if __name__=="__main__":unittest.main()
