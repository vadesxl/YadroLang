import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RuntimeGuardAdversarialDesignTests(unittest.TestCase):
 def review(self):return (ROOT/"RUNTIME_GUARD_ADVERSARIAL_REVIEW.md").read_text(encoding="utf-8")
 def test_review_remains_design_only(self):self.assertIn("no runtime enforcement is implemented",self.review())
 def test_stale_signed_policy_is_rejected(self):
  text=self.review();self.assertIn("correctly signed but stale policy",text);self.assertIn("rollback-resistant storage",text);self.assertIn("Wall-clock time alone is not an anti-rollback control",text)
 def test_authorization_is_bound_to_actual_use(self):
  text=self.review()
  for attack in ("DNS rebinding","proxy redirects","descriptor replacement","process handoff"):
   with self.subTest(attack=attack):self.assertIn(attack,text)
  self.assertIn("require a new decision",text)
 def test_port_filtering_is_not_misrepresented_as_complete_mediation(self):
  text=self.review()
  for surface in ("UDP/QUIC","raw sockets","ICMP","Unix sockets","named pipes","inherited descriptors","shared memory","clipboard"):
   with self.subTest(surface=surface):self.assertIn(surface,text)
  self.assertIn("refuses startup",text)
 def test_quarantine_and_alert_fail_closed(self):
  text=self.review();self.assertIn("Alert loss cannot release or weaken quarantine",text);self.assertIn("Partial adapter failure moves to `FAIL_SAFE`",text);self.assertIn("blindly killing a process is forbidden",text)
 def test_heuristics_never_grant_or_declassify(self):
  text=self.review();self.assertIn("cannot grant access, declassify data or release quarantine",text)
 def test_identity_and_telemetry_are_hardened(self):
  text=self.review();self.assertIn("Path, filename, PID and process name are not artifact identity",text);self.assertIn("do not echo marked secret fixtures",text);self.assertIn("cannot be enabled by the protected process",text)
if __name__=="__main__":unittest.main()
