import json,unittest
from src.proof_seal_verify import *
from tests.proof_verify_fixtures import valid_bytes,parsed,encoded
class ProofVerifyCanonicalTests(unittest.TestCase):
 def test_inspect_vs_verify(self):
  inspected=inspect_bytes(valid_bytes());verified=verify_bytes(valid_bytes());self.assertTrue(inspected.valid);self.assertFalse(inspected.verified);self.assertTrue(verified.verified);self.assertEqual("unsigned",verified.trust_mode);self.assertEqual("not-provided",verified.authenticity)
 def test_alternate_encodings_rejected_only_by_verify(self):
  variants=(encoded(parsed(),indent=2),encoded(parsed(),ascii=True),valid_bytes().rstrip(b"\n"),valid_bytes()+b"\n")
  for data in variants:
   with self.subTest(size=len(data)):self.assertTrue(inspect_bytes(data).valid);self.assertEqual(ProofCanonicalError.code,verify_bytes(data).diagnostic_code)
 def test_digest_mutations(self):
  for section,key in (("trust","mode"),("compiler","version"),("subject","target_triple")):
   value=parsed();value[section][key]="changed";result=verify_bytes(encoded(value));self.assertFalse(result.valid);self.assertIn(result.diagnostic_code,{ProofDigestError.code,ProofValueError.code})
  value=parsed();value["seal_sha256"]="f"*64;self.assertEqual(ProofDigestError.code,verify_bytes(encoded(value)).diagnostic_code)
if __name__=="__main__":unittest.main()
