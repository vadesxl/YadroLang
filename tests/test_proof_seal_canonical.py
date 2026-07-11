import json,unittest
from src.proof_seal import *
from tests.proof_seal_fixtures import minimal_core,rich_core
class ProofSealCanonicalTests(unittest.TestCase):
 def test_minimal_bytes_are_stable(self):
  first=canonical_bytes(minimal_core());second=canonical_bytes(minimal_core());self.assertEqual(first,second);self.assertTrue(first.endswith(b"\n"));self.assertNotIn(b" ",first)
 def test_rich_bytes_are_order_independent(self):self.assertEqual(canonical_bytes(rich_core(False)),canonical_bytes(rich_core(True)))
 def test_serialized_call_identity_is_complete_without_frontend_duplication(self):
  value=json.loads(canonical_bytes(rich_core()));call=value["analysis"]["call_sites"][0]
  self.assertIn("module_id",call);self.assertEqual("call",call["semantic_kind"]);self.assertNotIn("frontend",call);self.assertEqual("ru",value["compiler"]["frontend"])
 def test_seal_round_trip_shape(self):
  proof=seal(rich_core());value=json.loads(canonical_bytes(proof));self.assertEqual(proof.seal_sha256,value["seal_sha256"]);self.assertEqual(SCHEMA,value["schema"])
if __name__=="__main__":unittest.main()
