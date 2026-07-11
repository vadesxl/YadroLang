import unittest
from src.proof_seal import MAX_SAFE_INTEGER,call_site_id
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import parsed,encoded
class ProofVerifyStructureTests(unittest.TestCase):
 def test_unknown_and_missing_fields(self):
  value=parsed();value["trust"]["extra"]=1;self.assertEqual(ProofStructureError.code,inspect_bytes(encoded(value)).diagnostic_code)
  value=parsed();del value["compiler"]["frontend"];self.assertEqual(ProofStructureError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_bool_integer_confusion(self):
  value=parsed();value["analysis"]["fixpoint"]["updates"]=True;self.assertEqual(ProofValueError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_safe_integer_cross_layer(self):
  value=parsed();call=value["analysis"]["call_sites"][0];call["span"].update({"start_byte":MAX_SAFE_INTEGER,"end_byte":MAX_SAFE_INTEGER,"ordinal":MAX_SAFE_INTEGER});span=call["span"];call["id"]=call_site_id(value["compiler"]["frontend"],call["module_id"],call["caller"],call["callee"],call["semantic_kind"],span["start_byte"],span["end_byte"],span["ordinal"]);value["analysis"]["fixpoint"].update({"updates":MAX_SAFE_INTEGER,"bound":MAX_SAFE_INTEGER});self.assertTrue(inspect_bytes(encoded(value)).valid)
  for invalid in (MAX_SAFE_INTEGER+1,9_999_999_999_999_999,18_446_744_073_709_551_615,-1,False,1.0):
   with self.subTest(value=invalid):
    value=parsed();value["analysis"]["fixpoint"]["updates"]=invalid;self.assertEqual(ProofValueError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_order_and_duplicates(self):
  value=parsed();labels=value["analysis"]["call_sites"][0]["incoming_labels"];labels.reverse();self.assertEqual(ProofOrderingError.code,inspect_bytes(encoded(value)).diagnostic_code)
  value=parsed();value["analysis"]["entry_points"]*=2;self.assertEqual(ProofOrderingError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_broken_reference(self):
  value=parsed();value["analysis"]["call_sites"][0]["assumption_ids"]=["f"*64];self.assertEqual(ProofReferenceError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_forged_assumption_id(self):
  value=parsed();value["analysis"]["assumptions"][0]["id"]="f"*64;self.assertEqual(ProofReferenceError.code,inspect_bytes(encoded(value)).diagnostic_code)
if __name__=="__main__":unittest.main()
