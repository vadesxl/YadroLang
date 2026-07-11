import dataclasses,unittest
from src.proof_seal import *
from tests.proof_seal_fixtures import minimal_core,ZERO
class ProofSealAdversarialTests(unittest.TestCase):
 def test_non_nfc_and_controls(self):
  for value in ("e\u0301","bad\x00name","bad\x01name"):
   with self.subTest(value=value),self.assertRaises(ProofSealError):CompilerIdentity("yadro-guard",value,"ru","1.0")
 def test_invalid_trust_and_versions(self):
  with self.assertRaises(ProofSealError):TrustState("signed","verified")
  with self.assertRaises(ProofSealError):SubjectBinding("future",LLVM_NORMALIZATION_VERSION,ZERO,ZERO,ZERO,ZERO,"x","elf-object")
  with self.assertRaises(ProofSealError):SubjectBinding(POLICY_VERSION,"future",ZERO,ZERO,ZERO,ZERO,"x","elf-object")
 def test_invalid_span_and_safe_integer_overflow(self):
  invalid=((-1,0,0),(2,1,0),(0,1,-1),(True,1,0),(0,MAX_SAFE_INTEGER+1,0),(0,1,MAX_SAFE_INTEGER+1))
  for start,end,ordinal in invalid:
   with self.subTest(values=(start,end,ordinal)),self.assertRaises(ProofSealError):SourceSpan("x",start,end,ordinal)
  for value in (9_007_199_254_740_992,9_999_999_999_999_999,18_446_744_073_709_551_615,False,1.0):
   with self.subTest(value=value),self.assertRaises(ProofSealError):FixpointEvidence("bounded-monotone-1.0",(),value,MAX_SAFE_INTEGER)
 def test_duplicate_sets_and_ids(self):
  with self.assertRaises(ProofSealError):canonical_strings(("a","a"),"labels")
  assumption=make_assumption("sym","i64()",None,"identity",False,"call",False)
  with self.assertRaises(ProofSealError):make_analysis(assumptions=(assumption,assumption))
 def test_forged_content_ids_fail(self):
  assumption=make_assumption("sym","i64()",None,"identity",False,"call",False)
  with self.assertRaises(ProofSealError):ExternalAssumption(ZERO,assumption.symbol,assumption.abi_signature,None,"identity",False,"call",False,None)
  with self.assertRaises(ProofSealError):ProofSeal(minimal_core(),ZERO)
 def test_excessive_sets(self):
  with self.assertRaises(ProofSealError):canonical_strings(tuple(f"x{i}" for i in range(MAX_SEMANTIC_SET+1)),"labels")
 def test_invalid_flags_source_and_serializer(self):
  with self.assertRaises(ProofSealError):make_assumption("s","i64()",None,"identity",1,"call",False)
  with self.assertRaises(ProofSealError):module_id("ru","not bytes")
  with self.assertRaises(ProofSealError):canonical_bytes({"schema":SCHEMA})
 def test_unsupported_frontend_and_artifact(self):
  with self.assertRaises(ProofSealError):module_id("fr",b"x")
  with self.assertRaises(ProofSealError):SubjectBinding(POLICY_VERSION,LLVM_NORMALIZATION_VERSION,ZERO,ZERO,ZERO,ZERO,"x","pe-exe")
 def test_frozen(self):
  with self.assertRaises(dataclasses.FrozenInstanceError):minimal_core().trust.mode="signed"
if __name__=="__main__":unittest.main()
