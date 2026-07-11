import unittest
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import parsed,encoded
class ProofVerifyStructureTests(unittest.TestCase):
 def test_unknown_and_missing_fields(self):
  value=parsed();value["trust"]["extra"]=1;self.assertEqual(ProofStructureError.code,inspect_bytes(encoded(value)).diagnostic_code)
  value=parsed();del value["compiler"]["frontend"];self.assertEqual(ProofStructureError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_bool_integer_confusion(self):
  value=parsed();value["analysis"]["fixpoint"]["updates"]=True;self.assertEqual(ProofValueError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_order_and_duplicates(self):
  value=parsed();labels=value["analysis"]["call_sites"][0]["incoming_labels"];labels.reverse();self.assertEqual(ProofOrderingError.code,inspect_bytes(encoded(value)).diagnostic_code)
  value=parsed();value["analysis"]["entry_points"]*=2;self.assertEqual(ProofOrderingError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_broken_reference(self):
  value=parsed();value["analysis"]["call_sites"][0]["assumption_ids"]=["f"*64];self.assertEqual(ProofReferenceError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_forged_assumption_id(self):
  value=parsed();value["analysis"]["assumptions"][0]["id"]="f"*64;self.assertEqual(ProofReferenceError.code,inspect_bytes(encoded(value)).diagnostic_code)
if __name__=="__main__":unittest.main()
