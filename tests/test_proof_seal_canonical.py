import unittest
from src.proof_seal import *
from tests.proof_seal_fixtures import minimal_core,rich_core
class ProofSealCanonicalTests(unittest.TestCase):
 def test_deterministic_and_utf8(self):
  data=canonical_bytes(rich_core());self.assertTrue(data.endswith(b"\n"));self.assertFalse(data.endswith(b"\n\n"));self.assertIn("ПДн".encode(),data);self.assertNotIn(b"\\u041f",data);self.assertTrue(all(canonical_bytes(rich_core())==data for _ in range(100)))
 def test_compact_and_slash(self):
  data=canonical_bytes(rich_core());self.assertNotIn(b": ",data);self.assertIn(b"src/",data);self.assertNotIn(b"src\\/",data)
 def test_quote_and_backslash_escaping(self):
  assumption=make_assumption('a"b\\c',"i64()",None,"identity",False,"call",False);data=canonical_bytes(ProofSealCore(minimal_core().compiler,minimal_core().subject,make_analysis(assumptions=(assumption,))));self.assertIn(b'a\\"b\\\\c',data)
 def test_controls_rejected_before_serialization(self):
  for value in ("line\n","tab\t","control\x01"):
   with self.subTest(value=value),self.assertRaises(ProofSealError):make_assumption("a","i64()",None,value,False,"call",False)
 def test_seal_is_stable_and_full(self):
  proof=seal(minimal_core());self.assertRegex(proof.seal_sha256,r"^[0-9a-f]{64}$");data=canonical_bytes(proof);self.assertIn(b'"seal_sha256"',data);self.assertEqual(data,canonical_bytes(seal(minimal_core())))
 def test_reject_arbitrary_mapping(self):
  with self.assertRaises(ProofSealError):canonical_bytes({"schema":SCHEMA})
if __name__=="__main__":unittest.main()
