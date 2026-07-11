import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class StringMemoryModelDesignTests(unittest.TestCase):
 def test_abi_symbol_templates_remain_exact(self):
  abi=(ROOT/"ABI.md").read_text(encoding="utf-8")
  self.assertIn("`yadro_fn_<readable>_<sha256-prefix>`",abi)
  self.assertIn("`yadro_abi_v1_<readable>_<sha256-prefix>`",abi)
 def test_borrowed_view_contract_is_explicit(self):
  model=(ROOT/"STRING_MEMORY_MODEL.md").read_text(encoding="utf-8")
  for invariant in ("string = { data: *const u8, len: u64 }","возврат `string` запрещен","const uint8_t *data, uint64_t len","unknown` fail-closed","не использовать `inbounds getelementptr`"):
   with self.subTest(invariant=invariant):self.assertIn(invariant,model)
 def test_design_does_not_claim_current_backend_is_safe(self):
  abi=(ROOT/"ABI.md").read_text(encoding="utf-8");model=(ROOT/"STRING_MEMORY_MODEL.md").read_text(encoding="utf-8")
  self.assertIn("Текущий pointer-only lowering",abi);self.assertIn("Статус: нормативный дизайн до реализации",model)
if __name__=="__main__":unittest.main()
