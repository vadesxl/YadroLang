import unittest
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import parsed,encoded,valid_bytes
class ProofVerifyPreflightTests(unittest.TestCase):
 def test_supported(self):self.assertTrue(inspect_bytes(valid_bytes()).valid)
 def test_future_versions(self):
  for path in (("schema",),("subject","policy_schema_version"),("subject","llvm_normalization_version")):
   value=parsed();target=value
   for key in path[:-1]:target=target[key]
   target[path[-1]]="future"
   self.assertEqual(ProofVersionError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_missing_or_wrong_versions(self):
  value=parsed();del value["subject"]["policy_schema_version"];self.assertEqual(ProofVersionError.code,inspect_bytes(encoded(value)).diagnostic_code)
  value=parsed();value["schema"]=1;self.assertEqual(ProofValueError.code,inspect_bytes(encoded(value)).diagnostic_code)
 def test_duplicate_keys_nested(self):
  data=valid_bytes().replace(b'"mode":"unsigned"',b'"mode":"unsigned","mode":"unsigned"')
  self.assertEqual(ProofDuplicateKeyError.code,inspect_bytes(data).diagnostic_code)
if __name__=="__main__":unittest.main()
