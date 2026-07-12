import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RuntimeGuardDesignTests(unittest.TestCase):
 def model(self):return (ROOT/"RUNTIME_GUARD_DESIGN.md").read_text(encoding="utf-8")
 def test_design_is_not_misrepresented_as_implemented(self):
  text=self.model();self.assertIn("В 2.1.0 не реализован",text);self.assertIn("не является свойством компилятора",text)
 def test_layered_containment_contract_is_explicit(self):
  text=self.model()
  for invariant in ("Capability broker","Egress mediator","Port exposure policy","Scan detection","Quarantine","Owner alert","Missing enforcement support is a hard startup failure"):
   with self.subTest(invariant=invariant):self.assertIn(invariant,text)
 def test_quarantine_cannot_be_released_by_untrusted_code(self):
  text=self.model();self.assertIn("Untrusted code cannot move to a less restrictive state",text);self.assertIn("do not release quarantine",text)
 def test_monitoring_cannot_become_an_attack_or_exfiltration_channel(self):
  text=self.model();self.assertIn("не запускает встречное сканирование",text);self.assertIn("No counter-scanning, exploitation, retaliation",text);self.assertIn("Logs must not become a second exfiltration channel",text)
 def test_ethical_contract_rejects_silent_sacrifice_optimization(self):
  text=self.model();self.assertIn("cannot silently declassify a protected interest",text);self.assertIn("Inaction is modeled as an action",text);self.assertIn("multi-party, time-bounded, logged",text)
if __name__=="__main__":unittest.main()
